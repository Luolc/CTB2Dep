from convertor import Convertor

convertor = Convertor('head_rules.txt')

with open('ctb.bracketed', 'r') as f_in, open('ctb.conll', 'w') as f_out:
    for line in f_in:
        if line.startswith('#'):
            f_out.write(line)
        else:
            deps = convertor.convert(line)
            f_out.write(deps + '\n')
