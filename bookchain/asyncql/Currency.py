from decimal import Decimal
from sqloquent.asyncql import AsyncHashedModel


class Currency(AsyncHashedModel):
    connection_info: str = ''
    table: str = 'currencies'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'name', 'prefix_symbol', 'postfix_symbol',
        'fx_symbol', 'unit_divisions', 'base', 'details'
    )
    id: str
    name: str
    prefix_symbol: str|None
    postfix_symbol: str|None
    fx_symbol: str|None
    unit_divisions: int
    base: int|None
    details: str|None

    def to_decimal(self, amount: int) -> Decimal:
        """Convert the amount into a Decimal representation."""
        base = self.base or 10
        return Decimal(amount) / Decimal(base**self.unit_divisions)

    def get_units(self, amount: int) -> tuple[int,]:
        """Get the full units and subunits."""
        def get_subunits(amount, base, unit_divisions):
            units_and_change = list(divmod(amount, base ** unit_divisions))
            if unit_divisions > 1:
                units_and_change = [units_and_change[0], *get_subunits(units_and_change[1], base, unit_divisions-1)]
            return units_and_change
        base = self.base or 10
        unit_divisions = self.unit_divisions
        return get_subunits(amount, base, unit_divisions)

    def format(self, amount: int, *, unit_divisions: int = None,
               use_prefix: bool = True, use_postfix: bool = False,
               use_fx_symbol: bool = False) -> str:
        """Format an amount using the correct number of unit_divisions."""
        if not unit_divisions:
            unit_divisions = self.unit_divisions

        amount: str = str(self.to_decimal(amount))
        if '.' not in amount:
            amount += '.'
        digits = len(amount.split('.')[1])

        while digits < unit_divisions:
            amount += '0'
            digits += 1

        if self.postfix_symbol and use_postfix:
            return f"{amount}{self.postfix_symbol}"

        if self.fx_symbol and use_fx_symbol:
            return f"{amount} {self.fx_symbol}"

        if self.prefix_symbol and use_prefix:
            return f"{self.prefix_symbol}{amount}"

        return amount
