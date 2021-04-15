#!/usr/bin/env python
"""
Knapsack Solver with basic genetic algo
Dont expect docstring!
"""
from dataclasses import dataclass, field, asdict
from typing import ClassVar
from itertools import zip_longest, chain
from random import choice, randrange
from bisect import bisect_left
from functools import lru_cache
from time import time

# from secrets import choice, randbelow
import yaml


defaults_params = {
    "sack_max_weight": 5000000,
    "nb_item": 50000,
    "value_min": 1,
    "value_max": 100000,
    "weight_min": 1,
    "weight_max": 100000,
    "pool_size": 500,
    "pool_keep_best": 250,
    "pool_add_random_low": 10,
    "pool_add_random_high": 50,
    "rounds": 500,
}

PARAMS_FILE = "params.yml"
ITEMS_FILE = "items.yml"
HIGH_SCORE = "high_score.yml"
CACHE_RATIO = 3
all_items = None
cache_per_wlimit = {}
cache_entries = {}


def read_params():
    try:
        with open(PARAMS_FILE) as f:
            return yaml.load(f, yaml.SafeLoader)
    except IOError:
        return defaults_params


def read_high_score():
    try:
        with open(HIGH_SCORE) as f:
            return yaml.load(f, yaml.SafeLoader)["value"]
    except IOError:
        return 0


def dump_high_score(winner):
    with open(HIGH_SCORE, "w") as f:
        yaml.dump(winner.deep_dict(), f)


@dataclass(frozen=True)
class Item:
    # id: int
    weight: int
    value: int

    __annotations__ = {
        "weight": int,
        "value": int,
    }


def spent(t0, t):
    m, s = divmod(t - t0, 60)
    m = int(m)
    if m == 0:
        return f"{s:.2f}s"
    return f"{m}m{s:.2f}s"


def line():
    print("-" * 80)


def read_items():
    line()
    print("Reading", ITEMS_FILE)
    with open(ITEMS_FILE) as f:
        content = yaml.load(f, yaml.SafeLoader)
    # return tuple(Item(i[0], i[1], i[2]) for i in content["items"])
    return tuple(Item(i[0], i[1]) for i in content["items"])


@dataclass(frozen=False, order=True)
class Sack:
    items: list = field(default_factory=list, init=True, compare=False)
    id: int = field(default=0, init=False, compare=False)
    weight: int = field(default=0, init=False, compare=False)
    value: int = field(default=0, init=False, compare=True)
    cpt_solution_id: ClassVar[int] = 0

    # for cython
    __annotations__ = {
        "items": list,
        "id": int,
        "weight": int,
        "value": int,
        "cpt_solution_id": ClassVar[int],
    }

    def __post_init__(self):
        Sack.cpt_solution_id += 1
        self.id = Sack.cpt_solution_id
        # self.sort_items() never, it's bad.
        self.update_weight()
        self.update_value()

    def update_weight(self):
        self.weight = sum(i.weight for i in self.items) if self.items else 0

    def update_value(self):
        self.value = sum(i.value for i in self.items) if self.items else 0

    def short_repr(self):
        return f"<Sack value={self.value:,} weight={self.weight:,} qt={len(self.items)} #{self.id}>"

    # def sort_items(self):
    #     self.items.sort()
    #     self.items.reverse()

    def deep_dict(self):
        d = asdict(self)
        d["items"] = [asdict(i) for i in self.items]
        return d


def low_weight_all_items(wlimit):
    if wlimit in cache_entries["wt"]:
        return _low_weight_all_items(wlimit)
    return low_weight_threshold(wlimit)


@lru_cache(maxsize=2048)
def low_weight_threshold(wlimit):
    idx = bisect_left(cache_entries["wt_sorted"], wlimit)
    if idx == len(cache_entries["wt"]):
        return []
    return _low_weight_all_items(idx)


def _low_weight_all_items(wlimit):
    if wlimit not in cache_per_wlimit:
        cache_per_wlimit[wlimit] = [i for i in all_items if i.weight <= wlimit]
    return cache_per_wlimit[wlimit]


def pre_cache():
    wt = {i.weight for i in all_items}
    wt_sorted = sorted(list(wt))
    cache_entries["wt"] = wt
    cache_entries["wt_sorted"] = wt_sorted
    cache_per_wlimit[0] = all_items
    for w in wt_sorted[: len(all_items) // CACHE_RATIO]:
        r = [i for i in all_items if i.weight <= w]
        cache_per_wlimit[w] = r


def gen_random_Sack(p):
    chosen = []
    chosen_ids = set()
    lit = len(all_items)
    max_weight = p["sack_max_weight"]
    w = 0
    while True:
        if len(chosen_ids) >= lit:
            break
        # idx = randbelow(lit)
        idx = randrange(lit)
        if idx in chosen_ids:
            continue
        # assuming the general rule: len(items) >> quantity to choose
        i = all_items[idx]
        if w + i.weight > max_weight:
            break
        w += i.weight
        chosen.append(i)
        chosen_ids.add(idx)

    # finishing, try to find items small enough
    chosen2 = set(chosen)
    while True:
        wlimit = max_weight - w
        if wlimit < p["smaller_weight"]:
            break
        lw_items = low_weight_all_items(wlimit)
        if len(lw_items) > 5 * len(chosen2):
            while True:
                i = choice(lw_items)
                if i in chosen2:
                    continue
                break
        else:
            lw_items = [x for x in lw_items if x not in chosen2]
            if not lw_items:
                break
            i = choice(lw_items)
        w += i.weight
        chosen.append(i)
        chosen2.add(i)

    return Sack(items=chosen)


def mixed_Sack(p, a, b):
    chosen = set()
    max_weight = p["sack_max_weight"]
    w = 0
    for i in chain(*zip_longest(a.items, b.items)):
        if i and i not in chosen:
            if w + i.weight > max_weight:
                break
            w += i.weight
            chosen.add(i)
    # if we are too light, add some random:
    # finishing, try to find items small enough
    while True:
        wlimit = max_weight - w
        if wlimit < p["smaller_weight"]:
            break
        lw_items = low_weight_all_items(wlimit)
        if len(lw_items) > 5 * len(chosen):
            while True:
                i = choice(lw_items)
                if i in chosen:
                    continue
                break
        else:
            lw_items = [x for x in lw_items if x not in chosen]
            if not lw_items:
                break
            i = choice(lw_items)
        w += i.weight
        chosen.add(i)

    return Sack(items=list(chosen))


def print_pool(pool):
    line()
    print(", ".join(s.short_repr() for s in pool))
    line()


def init_pool(p):
    pool = list(gen_random_Sack(p) for _i in range(p["pool_size"]))
    print(f"generated {len(pool)} random Sacks")
    # print_pool(pool)
    return pool


def sort_pool(pool):
    return list(reversed(sorted(pool)))


def uniq(pool):
    # uniq on sorted list
    if not pool:
        return pool
    result = [pool[0]]
    for s in pool:
        if s != result[-1]:
            result.append(s)
    return result


def top_half_average(pool):
    top = len(pool) // 2
    return sum(i.value for i in pool[:top]) // top


def print_bests(top_average, pool):
    print(f"best of pool of {len(pool)}:")
    print("    ", pool[0].short_repr())
    print("    ", pool[1].short_repr())
    print("    ", pool[2].short_repr())
    print(f"average value top half: {top_average:,}")


def next_generation(round_nb, pool, more_random, p):
    # selection
    pool = uniq(sort_pool(pool))
    # remove the bad scores, keep the high scores:
    pool = pool[: p["pool_keep_best"]]  # keep high scores (like keep 20%)
    # add some random to the pool, aka ~mutation, (like adding 20 random)
    qt_random = p["pool_add_random_high"] if more_random else p["pool_add_random_low"]
    for _i in range(qt_random):
        pool.append(gen_random_Sack(p))
    # generate the pool by mixing
    # of 50% bests + 20 random
    new_pool = []
    while len(new_pool) < p["pool_size"]:
        while len(new_pool) < p["pool_size"]:
            cpt_err = 0
            while True:
                a = choice(pool)
                b = choice(pool)
                if a != b:
                    break
                cpt_err += 1
                if cpt_err >= 5:
                    break
            new_pool.append(mixed_Sack(p, a, b))
        new_pool = uniq(sort_pool(new_pool))
    pool = new_pool
    line()
    print("round", round_nb)
    top_average = top_half_average(pool)
    print_bests(top_average, pool)
    return pool, top_average


def check_high_score(winner):
    high_score = read_high_score()
    line()
    print(f"Result: {winner.value:,}")
    if winner.value > high_score:
        print("This is the high score !")
        dump_high_score(winner)
    else:
        print(f"Try again! The high score is currently {high_score:,}")
    line()


def find_smaller_weight():
    min_w = 2 ** 60
    for item in all_items:
        if item.weight < min_w:
            min_w = item.weight
    return min_w


def main():
    max_value = 0
    p = read_params()
    global all_items
    t0 = time()
    all_items = read_items()
    p["smaller_weight"] = find_smaller_weight()
    print(f"items: {len(all_items):,}", spent(t0, time()))
    print("caching...")
    t0 = time()
    pre_cache()
    print(spent(t0, time()))
    t0 = time()
    print("generate pool...")
    pool = init_pool(p)
    print(spent(t0, time()))
    more_random = False
    last_average = 0
    t0 = time()
    for i in range(1, p["rounds"] + 1):
        t1 = time()
        pool, top_average = next_generation(i, pool, more_random, p)
        more_random = bool(top_average <= last_average)
        last_average = top_average
        if pool[0].value > max_value:
            winner = pool[0]
            max_value = winner.value
            print("TOP:", winner.short_repr())
        else:
            print("top:", winner.short_repr())
        t = time()
        print(spent(t1, t), "cumul:", spent(t0, t), "av:", spent(0.0, (t - t0) / i))
    check_high_score(winner)


if __name__ == "__main__":
    main()
