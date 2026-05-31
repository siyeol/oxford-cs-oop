from collections import Counter, deque
from collections.abc import Iterator
from typing import Self


class Graph[N]:
    __slots__ = ("_adjacency",)

    _adjacency: dict[N, set[N]]

    def __new__(cls) -> Self:
        self = super().__new__(cls)
        self._adjacency = {}
        return self

    def add_node(self, node: N) -> None:
        if node not in self._adjacency:
            self._adjacency[node] = set()

    def add_edge(self, first: N, second: N) -> None:
        self.add_node(first)
        self.add_node(second)
        self._adjacency[first].add(second)
        self._adjacency[second].add(first)

    def neighbours(self, node: N) -> frozenset[N]:
        return frozenset(self._adjacency[node])

    def bfs(self, start: N, max_depth: int) -> Iterator[tuple[N, int]]:
        seen: set[N] = {start}
        queue: deque[tuple[N, int]] = deque([(start, 0)])
        while queue:
            node, depth = queue.popleft()
            yield node, depth
            if depth >= max_depth:
                continue
            for neighbour in self._adjacency[node]:
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append((neighbour, depth + 1))

    def __contains__(self, node: N) -> bool:
        return node in self._adjacency

    def __iter__(self) -> Iterator[N]:
        return iter(self._adjacency)

    def __len__(self) -> int:
        return len(self._adjacency)


class UnionFind[T]:
    __slots__ = ("_parent", "_rank")

    _parent: dict[T, T]
    _rank: dict[T, int]

    def __new__(cls) -> Self:
        self = super().__new__(cls)
        self._parent = {}
        self._rank = {}
        return self

    def add(self, item: T) -> None:
        if item not in self._parent:
            self._parent[item] = item
            self._rank[item] = 0

    def find(self, item: T) -> T:
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        cursor = item
        while self._parent[cursor] != root:
            self._parent[cursor], cursor = root, self._parent[cursor]
        return root

    def union(self, first: T, second: T) -> None:
        left, right = self.find(first), self.find(second)
        if left == right:
            return
        if self._rank[left] < self._rank[right]:
            left, right = right, left
        self._parent[right] = left
        if self._rank[left] == self._rank[right]:
            self._rank[left] += 1

    def connected(self, first: T, second: T) -> bool:
        return self.find(first) == self.find(second)

    def components(self) -> list[frozenset[T]]:
        groups: dict[T, set[T]] = {}
        for item in self._parent:
            groups.setdefault(self.find(item), set()).add(item)
        return [frozenset(members) for members in groups.values()]

    def __len__(self) -> int:
        return len(self._parent)


class Bag[T]:
    __slots__ = ("_counts",)

    _counts: Counter[T]

    def __new__(cls) -> Self:
        self = super().__new__(cls)
        self._counts = Counter()
        return self

    def add(self, item: T, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("amount must be non-negative")
        self._counts[item] += amount

    def remove(self, item: T, amount: int = 1) -> None:
        if amount < 0:
            raise ValueError("amount must be non-negative")
        if self._counts[item] < amount:
            raise ValueError("not enough items to remove")
        self._counts[item] -= amount
        if self._counts[item] == 0:
            del self._counts[item]

    def total(self) -> int:
        return sum(self._counts.values())

    def __getitem__(self, item: T) -> int:
        return self._counts[item]

    def __contains__(self, item: T) -> bool:
        return self._counts[item] > 0

    def __iter__(self) -> Iterator[T]:
        return iter(self._counts)

    def __len__(self) -> int:
        return len(self._counts)


class Stack[T]:
    __slots__ = ("_items",)

    _items: list[T]

    def __new__(cls) -> Self:
        self = super().__new__(cls)
        self._items = []
        return self

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        if not self._items:
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def peek(self) -> T:
        if not self._items:
            raise IndexError("peek from empty stack")
        return self._items[-1]

    def snapshot(self) -> tuple[T, ...]:
        return tuple(self._items)

    def replace(self, items: tuple[T, ...]) -> None:
        self._items = list(items)

    def __iter__(self) -> Iterator[T]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)
