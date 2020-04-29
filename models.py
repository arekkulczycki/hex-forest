from json import JSONEncoder


class Player:

    def __init__(self, id, websocket, name, present=True):
        self.id = id
        self.websocket = websocket
        self.name = name
        self.present = present

    def __str__(self):
        return str(self.id) if self else '...'


class DictEncoder(JSONEncoder):
    def default(self, o):
        d = o.__dict__
        try:
            del d['websocket']
        except KeyError:
            pass
        return d


class Board:

    def __init__(self, board_size=13):
        self.board_size = board_size
        self.rows = self.generate_rows(board_size)

    @staticmethod
    def generate_rows(board_size):
        rows = []
        for r in range(board_size):
            cells = []
            for c in range(board_size):
                cell = Cell(r, c)
                cells.append(cell)
            rows.append(cells)
        return rows


class Cell:

    def __init__(self, r, c):
        if r < 0 or c < 0:
            raise Exception
        self.id = f'{chr(c + 97)}{r + 1}'
        self.points = self.generate_points(r, c)
        self.width = 15.07
        self.state = 0  # 0-empty, 1-black, 2-white

    @classmethod
    def stone_x(cls, r, c):
        return 60.0 + c * 30 + r * 15

    @classmethod
    def stone_y(cls, r):
        return 30 + r * 25.98

    @staticmethod
    def generate_points(r, c):
        a_1 = 60.0 + c * 30 + r * 15
        a_2 = 47.4 + r * 25.98
        b_1 = 75.07 + c * 30 + r * 15
        b_2 = 38.70 + r * 25.98

        c_1 = 75.07 + c * 30 + r * 15
        c_2 = 21.30 + r * 25.98
        d_1 = 60.0 + c * 30 + r * 15
        d_2 = 12.60 + r * 25.98

        e_1 = 44.93 + c * 30 + r * 15
        e_2 = 21.30 + r * 25.98
        f_1 = 44.93 + c * 30 + r * 15
        f_2 = 38.70 + r * 25.98

        points = [
            '{:.2f},{:.2f}'.format(a_1, a_2),
            '{:.2f},{:.2f}'.format(b_1, b_2),
            '{:.2f},{:.2f}'.format(c_1, c_2),
            '{:.2f},{:.2f}'.format(d_1, d_2),
            '{:.2f},{:.2f}'.format(e_1, e_2),
            '{:.2f},{:.2f}'.format(f_1, f_2)
        ]
        return ' '.join(points)
