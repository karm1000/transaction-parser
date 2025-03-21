from transaction_parser.transaction_parser.document_generators.transaction import (
    TransactionGenerator,
)


class IndiaTransactionGenerator(TransactionGenerator):
    def get_company(self, company_obj, party_obj):
        # Validate GSTIN
        # search for gstin in company or address (get_party_for_gstin)

        # Validate PAN
        # search for pan in company or address (get_party_for_pan)

        # rapid fuzz with GSTIN

        # {"gstin": "company_name"}

        # rapid fuzz with PAN
        return super().get_company(company_obj, party_obj)

    def get_address(self, address_obj):
        pass

    pass
