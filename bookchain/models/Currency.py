from decimal import Decimal
from sqloquent import HashedModel


class Currency(HashedModel):
    connection_info: str = ''
    table: str = 'currencies'
    id_column: str = 'id'
    columns: tuple[str] = (
        'id', 'name', 'prefix_symbol', 'postfix_symbol',
        'fx_symbol', 'decimals', 'base', 'details'
    )
    id: str
    name: str
    prefix_symbol: str|None
    postfix_symbol: str|None
    fx_symbol: str|None
    decimals: int
    base: int|None
    details: str|None

    def to_decimal(self, amount: int) -> Decimal:
        """Convert the amount into a Decimal representation."""
        base = self.base or 10
        return Decimal(amount) / Decimal(base**self.decimals)

    def get_units_and_change(self, amount: int) -> tuple[int, int]:
        """Get the full units and subunits."""
        base = self.base or 10
        return divmod(amount, base ** self.decimals)

    def format(self, amount: int, *, decimals: int = None,
               use_prefix: bool = True, use_postfix: bool = False,
               use_fx_symbol: bool = False) -> str:
        """Format an amount using the correct number of decimals."""
        if not decimals:
            decimals = self.decimals

        amount: str = str(self.to_decimal(amount))
        if '.' not in amount:
            amount += '.'
        digits = len(amount.split('.')[1])

        while digits < decimals:
            amount += '0'
            digits += 1

        if self.postfix_symbol and use_postfix:
            return f"{amount}{self.postfix_symbol}"

        if self.fx_symbol and use_fx_symbol:
            return f"{amount} {self.fx_symbol}"

        if self.prefix_symbol and use_prefix:
            return f"{self.prefix_symbol}{amount}"

        return amount
