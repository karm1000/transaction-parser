class Transaction:
    DOCTYPE = None

    def __init__(self):
        if not self.DOCTYPE:
            raise NotImplementedError("DOCTYPE is not defined")

    def generate(self, parsed_data):
        raise NotImplementedError("generate() method must be implemented by subclass")
