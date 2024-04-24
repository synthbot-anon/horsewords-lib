import ast
import lark
import itertools

embed_header = r'''
%ignore " "
%import common.ESCAPED_STRING
%import common.CNAME

start : "{" embed "}" REST?
'''

embed_def = r'''
?embed : join
       | data
       '''

standard_fns = r'''
join : "join" data "with" string
'''

data_header = r'''
?data : string

?string : string_atom
        | string_atom string

?string_atom : '''

standard_data = r'''FIELD          -> field
             | ESCAPED_STRING -> esc_string
             | prod

prod : ESCAPED_STRING "*" COUNT

FIELD : ("." CNAME)+
COUNT : /\d+/
REST : /.+/s
'''

def create_embed_parser(embed_customizations, require_custom_fn=True, require_custom_field=True):
    grammar_parts = [embed_header, embed_def]
    if require_custom_fn:
        grammar_parts.append('| custom_fn')
    grammar_parts.append(embed_customizations)
    grammar_parts.append(standard_fns)
    grammar_parts.append(data_header)
    if require_custom_field:
        grammar_parts.append('custom_field\n | ')
    grammar_parts.append(standard_data)

    grammar = ''.join(grammar_parts)
    return lark.Lark(grammar, parser='earley')
    
@lark.v_args(inline=True)
class TemplatedString(lark.Transformer):
    def __init__(self, customizations, require_custom_fn=True, require_custom_field=True):
        self.data = None
        self.requirements = None
        self.parser = create_embed_parser(customizations, require_custom_fn, require_custom_field)
        self.endpos = -1
    
    def parse(self, template, data):
        startpos = 0
        result = []
        while startpos < len(template) - 1:
            # find the start of the template piece
            try:
                next_candidate = startpos + template[startpos:].index('{')
            except:
                result.append(template[startpos:])
                break
            
            # add all the crud before the template directly to the output
            if next_candidate != startpos:
                result.append(template[startpos:next_candidate])
                startpos = next_candidate

            # convert the template piece into a string
            try:
                self.data = data
                self.requirements = set()
                parsed_template = self.parser.parse(template[startpos:])
                fill_text = self.transform(parsed_template)

                # find the end of the template
                if len(parsed_template.children) == 1:
                    endpos = len(template) - 1
                else:
                    endpos = startpos + parsed_template.children[1].start_pos
                while template[endpos] != '}':
                    endpos -= 1
            except lark.exceptions.UnexpectedCharacters as e:
                print('lark exception:', e)
                fill_text = None
                endpos = 0

            # append the templated string and move the cursor to the next character
            if fill_text:
                result.append(fill_text)
                startpos = endpos + 1
            else:
                result.append(template[startpos])
                startpos += 1

        return ''.join(result)

    def start(self, embed, rest=None):
        return embed[0]({})
    
    def join(self, data, string):
        requirements = data[1].union(string[1])
        iterator = create_iterator(self.data, requirements)

        join_pieces = []
        for indexes in iterator:
            join_pieces.append(str(data[0](indexes)))
        
        result = string[0]({}).join(join_pieces)
        return lambda indexes: result, set()
        
    def string(self, atom, rest):
        gen = lambda indexes: f'{atom[0](indexes)}{rest[0](indexes)}'
        requirements = atom[1].union(rest[1])
        return gen, requirements
    
    def field(self, key_path):
        gen = lambda indexes: get_field(key_path, self.data, indexes)
        requirements = {key_path}
        return gen, requirements
    
    def esc_string(self, value):
        result = ast.literal_eval(value)
        gen = lambda indexes: result
        requirements = set()
        return gen, requirements
    
    def prod(self, string, count):
        result = ast.literal_eval(string) * int(count)
        gen = lambda indexes: result
        requirements = set()
        return gen, requirements



def get_field(key, data, indexes):
    current_field = ''

    for field in key.split('.')[1:]:
        current_field += f'.{field}'
        data = data[field]
        if current_field in indexes:
            idx = indexes[current_field]
            data = data[idx]
        
    return data

def walk_fields(key, data, indexes):
    current_field = ''
    field_parts = key.split('.')[1:]
    result = []
    current_data = [data]

    for idx, field in enumerate(field_parts):
        current_field += f'.{field}'
        current_data = [x[field] for x in current_data]

        if current_field in indexes:
            idx = indexes[current_field]
            current_data = [x[idx] for x in current_data]

        if type(current_data[0]) == list:
            current_data = itertools.chain(*current_data)

    return current_data


def get_field_tree(fields):
  intermediates = set()
  for leaf_field in fields:
      path = leaf_field[1:].split('.')
      for idx in range(1, len(path)):
          interim = f'.{".".join(path[:idx])}'
          intermediates.add(interim)
  return fields.union(intermediates)

def get_lists(data, allowed_descent):
  remaining = [(f'.{k}', v) for k,v in data.items()]
  result = set()

  while remaining:
    current_key, current_val = remaining.pop()

    if current_key not in allowed_descent:
      continue

    if type(current_val) == list:
      result.add(current_key)
      for next_val in current_val:
        remaining.append((current_key, next_val))

    if type(current_val) == dict:
      for next_key, next_val in current_val.items():
        remaining.append((f'{current_key}.{next_key}', next_val))

  return result

  
def create_iterator(data, requirements):
    all_fields = get_field_tree(requirements)
    all_lists = sorted(get_lists(data, all_fields))

    assert len(all_lists) == 1
    for idx in range(len(get_field(all_lists[0], data, {}))):
      yield {all_lists[0]: idx}
