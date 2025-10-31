import pandas as pd
from typing import Dict, Optional, Any, List

# --- 数据处理类 ---
import logging  # 导入 logging 模块


# --- 数据处理类 ---
class DataManager:
    def __init__(
        self, file_path: str, sheet_name: str, sn_column: str, result_columns: Dict[str, str], logger=None
    ):  # 添加类型注释
        self.file_path: str = file_path
        self.sheet_name: str = sheet_name
        self.sn_column: str = sn_column
        self.result_columns: Dict[str, str] = result_columns
        self.df: Optional[pd.DataFrame] = None  # 添加类型注释
        self.logger = logger or logging.getLogger(
            __name__
        )  # 使用传入的 logger 或创建新的

    def load_data(self) -> Optional[pd.DataFrame]:
        """
        从Excel文件加载数据，并准备结果列。
        """
        self.logger.info(f"正在从文件 '{self.file_path}' 读取数据...")
        try:
            self.df = pd.read_excel(self.file_path, sheet_name=self.sheet_name)
            self.logger.info("数据读取成功。")

            # 确保结果列存在，如果不存在则创建
            for col_name in self.result_columns.values():
                if col_name not in self.df.columns:
                    self.df[col_name] = None  # 或者使用 pd.NA
                    self.logger.warning(
                        f"Excel 文件中未找到结果列 '{col_name}'，已创建。"
                    )

            # 检查序列号列是否存在
            if self.sn_column not in self.df.columns:
                self.logger.error(f"Excel文件中未找到序列号列: '{self.sn_column}'")
                raise ValueError(f"Excel文件中未找到序列号列: '{self.sn_column}'")

            return self.df
        except FileNotFoundError:
            self.logger.error(
                f"错误：未找到文件 '{self.file_path}'。请检查文件路径是否正确。"
            )
            return None
        except ValueError as ve:
            self.logger.error(f"错误：{ve}")
            return None
        except Exception as e:
            self.logger.error(f"读取Excel文件时发生错误: {e}", exc_info=True)
            return None

    def save_data(self) -> None:
        """
        将DataFrame保存到Excel文件。
        """
        if self.df is not None:
            self.logger.info(f"正在将数据保存到文件 '{self.file_path}'...")
            try:
                self.df.to_excel(
                    self.file_path, sheet_name=self.sheet_name, index=False
                )
                self.logger.info("数据保存成功。")
            except FileNotFoundError:
                self.logger.error(
                    f"错误：保存文件时未找到路径 '{self.file_path}'。请检查路径是否有效。"
                )
            except PermissionError:
                self.logger.error(
                    f"错误：没有权限写入文件 '{self.file_path}'。请检查文件权限。"
                )
            except Exception as e:
                self.logger.error(f"保存Excel文件时发生错误: {e}", exc_info=True)
        else:
            self.logger.warning("DataFrame 为空，无需保存。")

    def update_result(self, index: Any, results: Dict[str, Any]) -> None:
        """
        更新DataFrame中指定行的查询结果。
        """
        if self.df is not None and index in self.df.index:
            # 使用 results 字典中的值完全覆盖 DataFrame 中对应行的结果列
            for excel_col_name, web_field_name in self.result_columns.items():
                 # 使用 get 方法，如果 results 中没有该字段，则设置为 None 或空字符串，而不是保留旧值
                 self.df.at[index, excel_col_name] = results.get(web_field_name, None)

            # 单独处理查询状态，确保它总是被更新
            self.df.at[index, "查询状态"] = results.get("查询状态", "未知错误")
            self.logger.debug(f"更新行索引 {index} 的结果: {results}")
        else:
            self.logger.warning(f"警告：尝试更新不存在的行索引 {index}。")

    def get_unqueried_serial_numbers(
        self, sn_column_name: str, status_column_name: str = "查询状态"
    ) -> List[tuple]:
        """
        获取DataFrame中查询状态不是“成功”的序列号及其索引。
        """
        if self.df is None:
            self.logger.warning("DataFrame 为空，无法获取未查询序列号。")
            return []

        unqueried = []
        for index, row in self.df.iterrows():
            # 检查查询状态是否不是“成功”或者为空
            if (
                pd.isna(row.get(status_column_name))
                or row.get(status_column_name) != "成功"
            ):
                unqueried.append((index, row[sn_column_name]))
        self.logger.info(f"找到 {len(unqueried)} 个未成功查询的序列号。")
        return unqueried
