def bubble_sort(seq: list[int]):
    changed = True
    while changed:
        changed = False
        for i in range(len(seq) - 1):
            if seq[i] > seq[i + 1]:
                seq[i], seq[i + 1] = seq[i + 1], seq[i]
                changed = True


v: list[int] = []
i = 10000
while i > 0:
    v.append(i)
    i -= 1
bubble_sort(v)
