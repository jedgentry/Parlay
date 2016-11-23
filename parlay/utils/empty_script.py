
class EmptyScript:

    def discover(self, force):
        raise Exception("You must call parlay.utils.setup() at the beginning of a script!")

    def get_item_by_id(self, item_id):
        raise Exception("You must call parlay.utils.setup() at the beginning of a script!")

    def get_item_by_name(self, item_name):
        raise Exception("You must call parlay.utils.setup() at the beginning of a script!")

    def get_all_items_with_name(self, item_name):
        raise Exception("You must call parlay.utils.setup() at the beginning of a script!")

    def sleep(self, item_name):
        raise Exception("You must call parlay.utils.setup() at the beginning of a script!")
