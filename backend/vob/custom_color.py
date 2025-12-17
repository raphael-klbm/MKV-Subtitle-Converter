from colour import Color

class CustomColor(Color):
    def __init__(self, *args, **kwargs) -> None:
        if kwargs.get('rgb', False) and len(kwargs['rgb']) > 3:
            self.a = kwargs['rgba'][0]
            kwargs['rgb'] = kwargs['rgba'][1:]
        super().__init__(*args, **kwargs)


    def __getattr__(self, label):
        try:
            if label.startswith("get_"):
                raise AttributeError("'%s' not found" % label)
            try:
                return getattr(self, 'get_' + label)()
            except AttributeError:
                raise AttributeError("'%s' not found" % label)
        except Exception:
            try:
                return self.__dict__[label]
            except (KeyError, RecursionError):
                raise AttributeError(name)

    def __setattr__(self, label, value):
        try:
            if label not in ["_hsl", "equality"]:
                fc = getattr(self, 'set_' + label)
                fc(value)
            else:
                self.__dict__[label] = value
        except Exception:
            try:
                self.__dict__[label] = value
            except (KeyError, RecursionError):
                raise AttributeError(name)
