from typing import Any

import pathway as pw


class OutputSchema(pw.Schema):
    ret: int


class AsyncIncrementTransformer(pw.AsyncTransformer, output_schema=OutputSchema):
    async def invoke(self, **kwargs) -> dict[str, Any]:
        # value = args[0]
        # name = args[1]
        # print(f"{value=}, {name=}")
        # await asyncio.sleep(0.1)
        return {"ret": kwargs["value"] + 1}


input = pw.debug.table_from_markdown("""
  | value | name
1 | 42    | vas
2 | 44    | geo
""")
result = AsyncIncrementTransformer(input_table=input).successful
pw.debug.compute_and_print(result, include_id=False)
