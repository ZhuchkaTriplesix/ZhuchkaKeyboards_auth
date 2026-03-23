from sqlalchemy.ext.asyncio import AsyncSession



class RootDAL:
    def __init__(self, session: AsyncSession):
        self.session = session
