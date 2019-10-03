from fixture import DataSet


class AddressData(DataSet):
    class dummy_address:
        street = "Seidenstraße"
        number = "1"
        zip_code = "01010"
        city = "Bielefeld"
        state = "Nordrhein-Westfalen"

    class dummy_address1:
        street = "Wundtstraße"
        number = "1"
        addition = "1-00"
        zip_code = "01217"

    class dummy_address2(dummy_address1):
        addition = "1-01"

    class dummy_address3(dummy_address1):
        number = "2"

    class dummy_address4(dummy_address3):
        addition = "2-00"

    class dummy_address5(dummy_address1):
        street = "Hochschulstraße"
