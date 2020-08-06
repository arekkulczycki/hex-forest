from models import DynamoDB


def bisect_left(a, x, lo=0, hi=None):
    if hi is None:
        hi = len(a)
    while lo < hi:
        mid = (lo+hi)//2
        if DynamoDB.position_move_bigger(x, a[mid]):
            lo = mid+1
        else:
            hi = mid
    return lo


def rest_if_is_subset_faster(moves, all_moves):
    indices = []
    n = len(all_moves)
    i = 0
    for move in moves:
        i = bisect_left(all_moves, move, i, n)
        if all_moves[i] != move:
            return False, None
        else:
            indices.append(i)

    rest = all_moves.copy()
    for i in sorted(indices, reverse=True):
        try:
            del rest[i]
        except IndexError:
            print(f'wrong index in REST: {i}, position length: {n}')

    return True, rest


# slow implementation (not using position order)
# TODO: # fast implementation (using position order)
def rest_if_is_subset(moves, moves_n, all_moves):
    rest = []
    rest_n = 0
    for move in all_moves:
        if move not in moves:
            rest.append(move)
            rest_n += 1
    is_subset = moves_n + rest_n == len(all_moves)
    return is_subset, rest


def position_outcome(outcomes, new_outcome):
    if outcomes is None:
        return {'results': [new_outcome], 'winner': new_outcome}
    outcomes['results'].append(new_outcome)
    results = outcomes['results']
    if len(results) >= 5:
        if len(set(results)) == 1:
            outcomes['winner'] = new_outcome
        else:
            outcomes['winner'] = 0
    else:
        outcomes['winner'] = None

    return outcomes