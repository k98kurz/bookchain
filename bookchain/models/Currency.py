from decimal import Decimal
from sqloquent import HashedModel, RelatedCollection


class Currency(HashedModel):
    connection_info: str = ''
    table: str = 'currencies'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'name', 'prefix_symbol', 'postfix_symbol',
        'fx_symbol', 'unit_divisions', 'base', 'details', 'description'
    )
    columns_excluded_from_hash: tuple[str] = ('description',)
    id: str
    name: str
    prefix_symbol: str|None
    postfix_symbol: str|None
    fx_symbol: str|None
    unit_divisions: int
    base: int|None
    details: str|None
    description: str|None
    ledgers: RelatedCollection

    # override automatic property
    @property
    def details(self) -> str|None:
        """A string stored in the database as text. Note that this will
            be changed to a packify.SerializableType stored as a blob in
            0.4.0.
        """
        return self.data.get('details', None)
    @details.setter
    def details(self, val: str|None):
        self.data['details'] = val

    def to_decimal(self, amount: int) -> Decimal:
        """Convert the amount into a Decimal representation."""
        base = self.base or 10
        return Decimal(amount) / Decimal(base**self.unit_divisions)

    def from_decimal(self, amount: Decimal) -> int:
        """Convert the amount from a Decimal representation."""
        base = self.base or 10
        return int(amount * base**self.unit_divisions)

    def get_units(self, amount: int) -> tuple[int,]:
        """Get the full units and subunits. The number of subunit
            figures will be equal to unit_divisions; e.g. if base=10
            and unit_divisions=2, get_units(200) will return (2, 0, 0);
            if base=60 and unit_divisions=2, get_units(200) will return
            (0, 3, 20).
        """
        def get_subunits(amount, base, unit_divisions):
            units_and_change = divmod(amount, base ** unit_divisions)
            if unit_divisions > 1:
                units_and_change = (
                    units_and_change[0],
                    *get_subunits(units_and_change[1], base, unit_divisions-1)
                )
            return units_and_change
        base = self.base or 10
        unit_divisions = self.unit_divisions
        return get_subunits(amount, base, unit_divisions)

    def format(
            self, amount: int, *,
            use_decimal: bool = True, decimal_places: int = 2,
            use_prefix: bool = True, use_postfix: bool = False,
            use_fx_symbol: bool = False, divider: str = '.'
        ) -> str:
        """Format an amount using the correct number of `decimal_places`.
            If `use_decimal` is `False`, instead the unit subdivisions
            from `get_units` will be combined using the `divider`
            char, and each part will be prefix padded with 0s to reach
            the `decimal_places`. E.g. `.format(200, use_decimal=False,
            divider=':') == '02:00'` for a Currency with `base=100` and
            `unit_divisions=1`.
        """
        if use_decimal:
            amount: str = str(self.to_decimal(amount))
            if '.' not in amount:
                amount += '.'
            digits = amount.split('.')[1]

            while len(digits) < decimal_places:
                digits += '0'

            digits = digits[:decimal_places]
            amount = f"{amount.split('.')[0]}.{digits}"
        else:
            units = self.get_units(amount)
            amount = ''
            for u in units:
                p = str(u)
                while len(p) < decimal_places:
                    p = "0" + p
                amount = f"{amount}:{p}"
            amount = amount[1:]

        if self.postfix_symbol and use_postfix:
            return f"{amount}{self.postfix_symbol}"

        if self.fx_symbol and use_fx_symbol:
            return f"{amount} {self.fx_symbol}"

        if self.prefix_symbol and use_prefix:
            return f"{self.prefix_symbol}{amount}"

        return amount
