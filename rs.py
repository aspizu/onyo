import re
from pathlib import Path



file = Path('src/main.rs').read_text()

struct = re.compile(r'struct (.*){\n([^}]*)\n}', re.MULTILINE)

for i in struct.findall(file):
    name = i[0].strip()
    i = i[1]
    fields: list[tuple[str, str]] = ([i.replace(',', '').strip().split(':') for i in i.split('\n') if not i.strip().startswith('//')])
    print(f'@dataclass\nclass {name}:')
    for field in fields:
        type = field[1].strip()
        vec = False
        if type.startswith('Vec<'):
            type = type.removeprefix('Vec<').removesuffix('>')
            vec = True
        if type == 'String':
            type = 'str'
        if type in ('usize', 'i64', 'i32', 'u64', 'u32'):
            type = 'int'
        if type in ('f64', 'f32'):
            type = 'float'
        if vec:
            type = f'list[{type}]'
        print(f'    {field[0]}: {type}')
    print()
