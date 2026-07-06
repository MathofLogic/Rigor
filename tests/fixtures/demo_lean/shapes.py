from abc import ABC, abstractmethod


class Shape(ABC):
    @abstractmethod
    def area(self): ...


class Circle(Shape):
    def __init__(self, r): self.r = r
    def area(self): return 3.14159 * self.r * self.r


class Square(Shape):
    def __init__(self, s): self.s = s
    def area(self): return self.s * self.s


def total_area(shapes):
    return sum(s.area() for s in shapes)
