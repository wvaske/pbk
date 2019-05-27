def islist(item):
    if hasattr(item, '__iter__') and not isinstance(item, str) and not hasattr(item, 'keys'):
        return True
    return False


def truncate_non_dicts(nested_item):
    def go_lower(item):
        """
        We go lower into a nested item if it is a list with complex items (more lists or dicts)
        or if it's a dictionary with complex items

        :param item:
        :return:
        """
        if islist(item):
            # If any of the list items are dictionaries, go lower
            if any([hasattr(i, 'keys') for i in item]):
                return True
        if hasattr(item, 'keys'):
            if any([any((hasattr(v, 'keys'), islist(v))) for v in item.values()]):
                return True
        return False

    if go_lower(nested_item):
        if islist(nested_item):
            return [truncate_non_dicts(item) for item in nested_item]
        elif hasattr(nested_item, 'keys'):
            return {k:truncate_non_dicts(v) for k, v in nested_item.items()}
        else:
            print('SHOUYLD NOT GET HERE!!!')
            return None
    else:
        if islist(nested_item) or hasattr(nested_item, 'keys'):
            return "[...]"
        else:
            return nested_item
