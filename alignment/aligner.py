import numpy as np
import pandas as pd
import argparse


class Aligner:
    """ Класс для получения локального или глобального выравнивания с константными штрафами """

    def __init__(self, seq1, seq2, match=1, gap=-1, mismatch=-1, weights=False, local=False):
        """
        Инициализация аргументов
        Args:
            seq1 (str): последовательность 1
            seq2 (str): последовательность 2
            match (float): вес совпадения
            gap (float): вес пропуска
            mismatch (float): вес несовпадения
            weights (str): название матрицы весов, может быть 'pam', 'blosum', а также False - весов нет
        """

        # делаем большими и красивыми
        self.seq1 = seq1.upper()
        self.seq2 = seq2.upper()
        self.match = np.float32(match)
        self.gap = np.float32(gap)
        self.mismatch = np.float32(mismatch)

        # используется ли локальное выравнивание
        self.local = local

        # устанавливаем веса
        self.weights = self.set_weights(weights)

        # инициализируем матрицу
        self.matrix = self.init_matrix()

    def check_non_negativity(self, result):
        if self.local:
            return max(0, result)
        return result

    def init_matrix(self):
        """
        Инициализация матрицы: сначала нулями, потом заполнение для добавленных спереди пропусков
        Returns:
            np.array: инициализированная матрица
        """

        # сначала инициализируем матрицу нулями по размерам посл1 + 1, посл2 + 1; + 1 за пропуск спереди
        matrix = np.zeros([len(self.seq1) + 1, len(self.seq2) + 1])

        if self.local:
            return matrix

        # это чтобы выстаскивать веса
        seq = ['-' + self.seq1, '-' + self.seq2]

        # заполняем первую строку и первый столбец
        for i, axis in enumerate(matrix.shape):
            counter = 0

            for ax in range(axis):
                position = (0, ax) if i else (ax, 0)

                # прибавляем вес сочетания пропуска и символа
                matrix[position] = counter + self.weights.loc[('-', seq[i][ax])]

                # заполнение последовательно += self.gap
                counter += self.gap + self.weights.loc[('-', seq[i][ax])]

        return matrix

    def align(self):
        """
        Получение матрицы по алгоритму Нидлмана-Вунша
        """

        # заполняем каждую клетку
        for i in range(1, len(self.seq1) + 1):
            for j in range(1, len(self.seq2) + 1):
                self.matrix[i, j] = self.check_non_negativity(self.cell(i, j))

        # печатаем получившуюся матрицу
        self.print_matrix()

    def print_matrix(self):
        """
        Печать матрицы по алгоритму Н-В
        """

        print(pd.DataFrame(data=self.matrix, index=list(' ' + self.seq1), columns=list(' ' + self.seq2)))

    def set_weights(self, weights):
        """
        Получение матрицы весов
        Args:
            weights (str): название матрицы весов, может быть 'pam', 'blosum', а также False - весов нет
        Returns:
            pd.DataFrame: матрица весов
        """

        if weights:
            if weights.lower() == 'pam':
                filename = 'alignment/PAM250.txt'
            elif weights.lower() == 'blosum':
                filename = 'alignment/BLOSUM62.txt'
            return pd.read_csv(filename, delimiter=' ', index_col=0, header=0)

        # заполняем веса 0
        else:
            seq = set(self.seq1 + self.seq2 + '-')

            return pd.DataFrame(np.zeros([len(seq), len(seq)]), index=seq,
                                columns=seq)

    def cell(self, i, j):
        """
        Заполнение клетки матрицы по Н-В
        Args:
            i (int): индекс элемента по оси 0
            j (int): индекс по оси 1
        Returns:
            float: значение в клетке
        """

        # символы, которые выравниваем
        seq1, seq2 = self.seq1[i - 1], self.seq2[j - 1]

        # получаем троих соседей
        idx = self.get_neighbours(i, j, make_tuple=True)

        # какие веса потребуются
        weights = [(seq1, seq2), (seq1, '-'), ('-', seq2)]

        # массив, из которого будем выбирать итоговое значение (максимум)
        available = []

        # итерируемся по парам индексов соседей и ключей весов
        for index, weight in zip(idx, weights):

            # для удобства запомним индексы соседей по осям отдельно
            first_index = index[0]
            second_index = index[1]

            # получаем текущий вес
            current_weight = self.weights.loc[weight]

            # получаем значение в клетке-соседе
            current_cell = self.matrix[index]

            # если идём по диагонали
            if (i - 1 == first_index) & (j - 1 == second_index):

                # если символы совпали, то прибавляем вес совпадения
                if seq1 == seq2:
                    current_cell += self.match

                # иначе - несовпадения
                else:
                    current_cell += self.mismatch

            # если не по диагонали, то это пропуск
            else:
                current_cell += self.gap

            # доавбляем вес
            current_cell += current_weight

            available.append(current_cell)
        return max(available)

    def print_alignment(self):
        """
        Красиво печатаем выравнивание
        """
        for cell in self.alignment:
            print(f'\nAlignment starts in cell {cell}:')
            for alignment in self.alignment[cell]:
                print('\t', *alignment[::-1])

    def get_neighbours(self, i, j, make_tuple=False):
        """
        Получаем индексы трёх соседей: слева, сверху и слева сверху по диагонали
        Args:
            i (int): индекс элемента по оси 0
            j (int): индекс элемента по оси 1
            make_tuple (bool): нужно ли возвращать пары индексов в tuple (сразу для индексации) или в list
        Returns:
            list: список пар индексов
        """

        result = [[i - 1, j - 1], [i, j - 1], [i - 1, j]]

        # если надо tuple, то делаем map
        if make_tuple:
            return list(map(tuple, result))
        return result

    def select_global_alignment(self):
        """
        Получение выравненных строк
        """

        # результат выравнивания
        self.alignment = [[], []]

        # значение, из которого пойдём - правый нижний край
        current = np.array(self.matrix.shape) - 1

        # конец (не интересует сочетание двух пропусков)
        end = np.array([1, 1])

        # пока не дошли до конца
        while np.any(current >= end):

            # запоминааем текущие индексы по осям
            first_index = current[0]
            second_index = current[1]

            # получаем троих соседей
            idx = self.get_neighbours(first_index, second_index)

            # выбираем только неотрицательные, на всякий случай
            idx = np.array([i for i in idx if ((i[0] >= 0) and (i[1] >= 0))])

            # значение в текущей клетке
            value = self.matrix[tuple(current)]

            # по каждому соседу
            for index in idx:

                # символы, которые сейчас сравниваем
                seq1 = self.seq1[current[0] - 1]
                seq2 = self.seq2[current[1] - 1]

                # значение в клетке-соседе
                backtrace = self.matrix[tuple(index)]

                # если идём по диагонали
                if np.array_equal(index + 1, current):

                    # берём вес от двух символов
                    weight = self.weights.loc[(seq1, seq2)]

                    # если символы совпадают и мы пришли из клетки по диагонали или символы по диагонали не совпали
                    if ((value - backtrace == self.match + weight) and (seq1 == seq2)) or \
                            (value - backtrace == self.mismatch + weight):

                        # добавляем в результат оба символа
                        self.alignment[0].append(seq1)
                        self.alignment[1].append(seq2)

                        # переходим в клетку-соседа
                        current = index
                        break

                # если идём наверх
                elif current[0] - index[0]:

                    # берём вес для символа первой последовательности и пропуска
                    weight = self.weights.loc[(seq1, '-')]
                    if value - backtrace == self.gap + weight:
                        self.alignment[0].append(seq1)
                        self.alignment[1].append('-')
                        current = index
                        break

                # если идём налево, то пропуск и символ второй последовательности
                else:
                    weight = self.weights.loc[('-', seq2)]
                    if value - backtrace == self.gap + weight:
                        self.alignment[0].append('-')
                        self.alignment[1].append(seq2)
                        current = index
                        break
        self.alignment = {tuple(np.array(self.matrix.shape) - 1): self.alignment}

    def select_local_alignment(self):
        matrix_max = self.matrix.max()
        indices = np.where(self.matrix == matrix_max)
        indices = [(x, y) for x, y in zip(*indices)]

        self.alignment = {}

        for start in indices:
            # значение в текущей клетке
            value = self.matrix[tuple(start)]
            current = start

            alignment = [[], []]

            while value != 0:
                # запоминааем текущие индексы по осям
                first_index = current[0]
                second_index = current[1]

                # получаем троих соседей
                idx = self.get_neighbours(first_index, second_index)

                # выбираем только неотрицательные, на всякий случай
                idx = np.array([i for i in idx if ((i[0] >= 0) and (i[1] >= 0))])

                # значение в текущей клетке
                value = self.matrix[tuple(current)]

                # по каждому соседу
                for index in idx:

                    # символы, которые сейчас сравниваем
                    seq1 = self.seq1[current[0] - 1]
                    seq2 = self.seq2[current[1] - 1]

                    # значение в клетке-соседе
                    backtrace = self.matrix[tuple(index)]

                    # если идём по диагонали
                    if np.array_equal(index + 1, current):

                        # берём вес от двух символов
                        weight = self.weights.loc[(seq1, seq2)]

                        # если символы совпадают и мы пришли из клетки по диагонали или символы по диагонали не совпали
                        if ((value - backtrace == self.match + weight) and (seq1 == seq2)) or \
                                (value - backtrace == self.mismatch + weight):
                            # добавляем в результат оба символа
                            alignment[0].append(seq1)
                            alignment[1].append(seq2)

                            # переходим в клетку-соседа
                            current = index
                            break

                    # если идём наверх
                    elif current[0] - index[0]:

                        # берём вес для символа первой последовательности и пропуска
                        weight = self.weights.loc[(seq1, '-')]
                        if value - backtrace == self.gap + weight:
                            alignment[0].append(seq1)
                            alignment[1].append('-')
                            current = index
                            break

                    # если идём налево, то пропуск и символ второй последовательности
                    else:
                        weight = self.weights.loc[('-', seq2)]
                        if value - backtrace == self.gap + weight:
                            alignment[0].append('-')
                            alignment[1].append(seq2)
                            current = index
                            break

            self.alignment[tuple(start)] = alignment


def parse_args(args=None):
    """ Функция, которая создает парсер для аргументов командной строки, и потом сама парсит аргументы и результат
    возвращает.
    Args:
        args: Параметры, которые необходимо распарсить вместо аргументов командной строки.
    Returns:
        Namespace: с параметрами, которые смогли распарсить.
    """

    parser = argparse.ArgumentParser(allow_abbrev=False, add_help=True, description="Alignment class")
    parser.add_argument("-seq1", "--seq1", required=True, default=None, type=str,
                        help="First sequence, any case.")
    parser.add_argument("-seq2", "--seq2", required=True, default=None, type=str,
                        help="Second sequence, any case.")
    parser.add_argument("-match", "--match", required=False, type=float, default=1,
                        help="Weight of match. Defaults to 1")

    parser.add_argument("-mismatch", "--mismatch", required=False, type=float, default=-1,
                        help="Weight of mismatch. Defaults to -1")

    parser.add_argument("-gap", "--gap", required=False, type=float, default=-1,
                        help="Weight of gap. Defaults to -1")
    parser.add_argument("-weights", "--weights", required=False, default=False,
                        help="Name of weight matrix. Default is no matrix.")
    parser.add_argument("-alignment", "--alignment", required=False, action='store_true', dest='alignment',
                        help="Print alignment")
    parser.add_argument("-local", "--local", required=False, action='store_true', dest='local',
                        help="Make local alignment")

    args = parser.parse_args(args)
    return args


def run(args=None):
    """
    Функция парсит аргументы командной строки и передает их в класс Aligner.
    Args:
        args: Аргументы, которые надо парсить. Если None, то парсим аргументы командной строки.
    """
    # Парсим аргументы командной строки или переданную строку с аргументами
    args = parse_args(args)

    print(f"Alignment started with parameters: {vars(args)}")

    # Создаем экземпляр модели
    # Передаем аргументы командной строки как параметры в метод __init__ модели
    aligner = Aligner(args.seq1, args.seq2, match=args.match, mismatch=args.mismatch, gap=args.gap,
                      weights=args.weights, local=args.local)

    # получаем матрицу
    aligner.align()

    # если надо вывести выравниваение, то выводим
    if args.alignment:
        if args.local:
            aligner.select_local_alignment()
        else:
            aligner.select_global_alignment()
        aligner.print_alignment()


if __name__ == "__main__":
    run()

