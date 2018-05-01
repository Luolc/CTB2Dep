from nltk.tree import ParentedTree


def _is_leaf(tree: ParentedTree):
    """
    Checks whether the given tree is a leaf.
    :param tree: a ParentedTree instance
    :return: true if it is a leaf
    """
    return tree.height() == 2


def _load_head_rules(fp: str):
    """
    Loads the head rules from the file with the given file path.
    :param fp: the file path
    :return: a dictionary of head rules
    """
    with open(fp, 'r') as f:
        rules = {}
        for line in f:
            tag, rule = line.split(':')
            rule = [sub_rule.split() for sub_rule in rule.split(';')]
            rule = [{'direction': sub_rule[0], 'tags': sub_rule[1:]} for sub_rule in rule]
            rules[tag] = rule
        return rules


def _preprosess(root: ParentedTree):
    """
    Preprocesses the lexcial tree: clean the syntactic tags and replace each token value with its
    index number.
    :param root: the root of the lexcial tree
    :return: a tuple of a processed tree and a sequence of (tag, token)
    """
    root: ParentedTree = root.copy(deep=True)

    def __iterate(tree: ParentedTree, index: int = 1):
        # clean the tags which contains '-'
        if '-' in tree.label():
            tree.set_label(tree.label().split('-')[0])
        if _is_leaf(tree):
            yield tree.label(), tree[0]  # (tag, token)
            tree[0] = index  # replace the token with its index number
            index += 1
        else:
            for subtree in tree:
                for _item in __iterate(subtree, index):
                    yield _item
                    index += 1

    # i.e. [('NR', '上海'), ('NR', '浦东'), ('NN', '开发'), ('CC', '与'), ...]
    sequences = [i for i in __iterate(root)]

    return root, sequences


def _get_relations(root: ParentedTree):
    """
    Gets the relations based on the phrase tree with head labels.
    :param root: a phrase tree with head labels
    :return: a sorted list of relation (index, parent_index)
    """
    def __iterate(tree: ParentedTree):
        # the index of the current node
        parent_index = tree.label().split('|')[0]

        # if this is the root node, yield a index -> 0 relation
        if not tree.parent():
            yield parent_index, 0

        if not _is_leaf(tree):
            for subtree in tree:
                index = subtree.label().split('|')[0]
                if index != parent_index:
                    yield index, parent_index
                for _item in __iterate(subtree):
                    yield _item

    return sorted(__iterate(root), key=lambda r: int(r[0]))


class Convertor:
    def __init__(self, head_rules_fp: str):
        self.head_rules = _load_head_rules(head_rules_fp)

    def convert(self, tree_str: str):
        """
        Converts a phrase tree (in string format) to dependency tree in CoNLL format.
        :param tree_str: a phrase tree in string format
        :return: dependency tree in CoNLL format (in string)
        """
        tree = ParentedTree.fromstring(tree_str)
        relations = self.__parse(tree)
        lines = ['{}\t{}\t_\t_\t{}\t_\t{}\tX\t_\t_'.format(*args) for args in relations]
        return '\n'.join(lines) + '\n'

    def __parse(self, tree: ParentedTree):
        """
        Parses an original phrase tree.
        :param tree: an original phrase tree
        :return: the dependency relations
        """
        tree, sequences = _preprosess(tree)
        tree = self.__mark_heads(tree)
        relations = _get_relations(tree)
        relations = [(index, value, tag, parent) for (tag, value), (index, parent) in
                     zip(sequences, relations)]
        return relations

    def __mark_heads(self, root: ParentedTree):
        """
        Marks the head of each phrase.
        :param root: a preprocessed phrase tree.
        :return: a phrase tree with head labels
        """
        root: ParentedTree = root.copy(deep=True)

        def __iterate(tree: ParentedTree):
            label = tree.label()

            if _is_leaf(tree):
                tree.set_label('{}|{}'.format(tree[0], label))
            else:
                for subtree in tree:
                    __iterate(subtree)

                # just select the last one as the head if the tag is not covered by the head rules
                if label not in self.head_rules:
                    index = tree[-1].label().split('|')[0]
                    tree.set_label('{}|{}'.format(index, label))
                    return

                for rule in self.head_rules[label]:
                    sub_labels = [t.label().split('|') for t in tree]
                    if rule['direction'] == 'r':
                        sub_labels = sub_labels[::-1]  # reverse

                    # this is the last rule, just select the first or last one as the head
                    if not rule['tags']:
                        index = sub_labels[0][0]
                        tree.set_label('{}|{}'.format(index, label))
                        return

                    for tag in rule['tags']:
                        if tag in {_tag for _i, _tag in sub_labels}:
                            index = next(_i for _i, _tag in sub_labels if tag == _tag)
                            tree.set_label('{}|{}'.format(index, label))
                            return

        __iterate(root)
        return root
