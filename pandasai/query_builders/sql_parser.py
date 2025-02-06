import sqlglot
from sqlglot import ParseError, exp, parse_one
from sqlglot.optimizer.qualify_columns import quote_identifiers


class SQLParser:
    @staticmethod
    def extract_table_names(query: str):
        parsed = sqlglot.parse_one(query)
        return {
            table.alias_or_name for table in parsed.find_all(sqlglot.expressions.Table)
        }

    @staticmethod
    def replace_table_and_column_names(query, table_mapping):
        """
        Transform a SQL query by replacing table names with either new table names or subqueries.

        Args:
            query (str): Original SQL query
            table_mapping (dict): Dictionary mapping original table names to either:
                           - actual table names (str)
                           - subqueries (str)
        """
        # Pre-parse all subqueries in mapping to avoid repeated parsing
        parsed_mapping = {}
        for key, value in table_mapping.items():
            try:
                parsed_mapping[key] = parse_one(value)
            except ParseError:
                raise ValueError(f"{value} is not a valid SQL expression")

        def transform_node(node):
            # Handle Table nodes
            if isinstance(node, exp.Table):
                original_name = node.name
                if original_name in table_mapping:
                    mapped_value = parsed_mapping[original_name]
                    if isinstance(mapped_value, exp.Alias):
                        return exp.Subquery(
                            this=mapped_value.this.this,
                            alias=node.alias or original_name,
                        )
                    return exp.Subquery(
                        this=mapped_value, alias=node.alias or original_name
                    )

            return node

        # Parse the SQL query
        parsed = parse_one(query)

        # Transform the query
        transformed = parsed.transform(transform_node)
        transformed = transformed.transform(quote_identifiers)

        # Convert back to SQL string
        return transformed.sql(pretty=True)
