import frappe


class Transaction:
    DOCTYPE = None

    def __init__(self):
        if not self.DOCTYPE:
            raise NotImplementedError("DOCTYPE is not defined")

    def generate(self, parsed_data):
        self.parsed_data = parsed_data
        self.doc = frappe.new_doc(self.DOCTYPE)

        self.set_details()
        self.set_flags()

        return self.doc.save()

    def set_details(self):
        # TODO: Implement
        pass

    def set_flags(self):
        self.doc.flags.ignore_permissions = True
        self.doc.flags.ignore_mandatory = True
        self.doc.flags.ignore_validate = True
        self.doc.flags.ignore_links = True
