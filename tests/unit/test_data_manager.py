# -*- coding: utf-8 -*-
"""
数据管理模块单元测试
"""
import pandas as pd
import tempfile
import os
from unittest.mock import patch, MagicMock
import pytest

import sys
sys.path.insert(0, 'src')

from ruijie_query.core.data_manager import DataManager


class TestDataManager:
    """DataManager类的单元测试"""

    def setup_method(self):
        """测试方法初始化"""
        self.temp_dir = tempfile.mkdtemp()
        self.excel_file = os.path.join(self.temp_dir, 'test_data.xlsx')

        # 创建测试数据
        self.test_data = pd.DataFrame({
            'Serial Number': ['SN001', 'SN002', 'SN003'],
            '型号': ['Model1', 'Model2', 'Model3'],
            '保修状态': [None, '成功', '失败']
        })

        # 保存测试数据到Excel文件
        self.test_data.to_excel(self.excel_file, sheet_name='Sheet1', index=False)

        self.result_columns = {
            '型号': '型号',
            '保修状态': '保修状态',
            '查询状态': '查询状态'
        }

        self.logger = MagicMock()
        self.data_manager = DataManager(
            file_path=self.excel_file,
            sheet_name='Sheet1',
            sn_column='Serial Number',
            result_columns=self.result_columns,
            logger=self.logger
        )

    def teardown_method(self):
        """测试方法清理"""
        if os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir)

    def test_init_with_logger(self):
        """测试使用自定义logger初始化"""
        logger = MagicMock()
        dm = DataManager(
            file_path=self.excel_file,
            sheet_name='Sheet1',
            sn_column='Serial Number',
            result_columns=self.result_columns,
            logger=logger
        )
        assert dm.logger == logger
        assert dm.file_path == self.excel_file
        assert dm.sheet_name == 'Sheet1'
        assert dm.sn_column == 'Serial Number'
        assert dm.result_columns == self.result_columns
        assert dm.df is None

    def test_init_without_logger(self):
        """测试不使用自定义logger初始化"""
        dm = DataManager(
            file_path=self.excel_file,
            sheet_name='Sheet1',
            sn_column='Serial Number',
            result_columns=self.result_columns
        )
        assert dm.logger is not None
        assert dm.df is None

    def test_load_data_success(self):
        """测试成功加载数据"""
        df = self.data_manager.load_data()

        assert df is not None
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert 'Serial Number' in df.columns
        assert '型号' in df.columns
        assert '保修状态' in df.columns

        # 检查是否添加了缺失的结果列
        assert '查询状态' in df.columns

        # 验证日志记录
        self.logger.info.assert_any_call(f"正在从文件 '{self.excel_file}' 读取数据...")
        self.logger.info.assert_any_call("数据读取成功。")

    def test_load_data_missing_sn_column(self):
        """测试加载数据时缺少序列号列"""
        # 创建一个没有序列号列的Excel文件
        wrong_excel_file = os.path.join(self.temp_dir, 'wrong_data.xlsx')
        wrong_data = pd.DataFrame({'Wrong Column': ['A', 'B', 'C']})
        wrong_data.to_excel(wrong_excel_file, sheet_name='Sheet1', index=False)

        dm = DataManager(
            file_path=wrong_excel_file,
            sheet_name='Sheet1',
            sn_column='Serial Number',
            result_columns=self.result_columns,
            logger=self.logger
        )

        df = dm.load_data()
        assert df is None
        self.logger.error.assert_any_call("Excel文件中未找到序列号列: 'Serial Number'")

    def test_load_data_missing_result_column(self):
        """测试加载数据时缺少结果列"""
        # 创建一个缺少某些结果列的Excel文件
        limited_data = pd.DataFrame({
            'Serial Number': ['SN001', 'SN002'],
            '型号': ['Model1', 'Model2']
        })
        limited_data.to_excel(self.excel_file, sheet_name='Sheet1', index=False)

        df = self.data_manager.load_data()
        assert df is not None
        # 检查是否自动添加了缺失的列
        assert '保修状态' in df.columns
        assert '查询状态' in df.columns
        self.logger.warning.assert_any_call("Excel 文件中未找到结果列 '保修状态'，已创建。")

    def test_load_data_file_not_found(self):
        """测试加载不存在的文件"""
        non_existent_file = os.path.join(self.temp_dir, 'non_existent.xlsx')
        dm = DataManager(
            file_path=non_existent_file,
            sheet_name='Sheet1',
            sn_column='Serial Number',
            result_columns=self.result_columns,
            logger=self.logger
        )

        df = dm.load_data()
        assert df is None
        self.logger.error.assert_any_call(f"错误：未找到文件 '{non_existent_file}'。请检查文件路径是否正确。")

    def test_load_data_exception(self):
        """测试加载数据时发生异常"""
        with patch('pandas.read_excel', side_effect=Exception("Test exception")):
            df = self.data_manager.load_data()
            assert df is None
            self.logger.error.assert_called()

    def test_save_data_success(self):
        """测试成功保存数据"""
        # 先加载数据
        df = self.data_manager.load_data()
        assert df is not None

        # 修改一些数据
        assert self.data_manager.df is not None
        self.data_manager.df.at[0, '查询状态'] = '成功'

        # 保存数据
        self.data_manager.save_data()

        # 验证文件是否被创建并包含正确数据
        assert os.path.exists(self.excel_file)

        # 重新读取验证
        saved_df = pd.read_excel(self.excel_file, sheet_name='Sheet1')
        assert len(saved_df) == 3
        assert saved_df.at[0, '查询状态'] == '成功'

        self.logger.info.assert_any_call(f"正在将数据保存到文件 '{self.excel_file}'...")
        self.logger.info.assert_any_call("数据保存成功。")

    def test_save_data_no_dataframe(self):
        """测试在没有DataFrame的情况下保存数据"""
        self.data_manager.save_data()
        # 应该记录警告
        self.logger.warning.assert_called_once_with("DataFrame 为空，无需保存。")

    def test_save_data_permission_error(self):
        """测试保存数据时权限错误"""
        # 先加载数据
        self.data_manager.load_data()

        # 模拟权限错误
        with patch.object(self.data_manager.df, 'to_excel', side_effect=PermissionError("Permission denied")):
            self.data_manager.save_data()
            self.logger.error.assert_called_once()

    def test_update_result_success(self):
        """测试成功更新查询结果"""
        # 先加载数据
        df = self.data_manager.load_data()
        assert df is not None

        # 更新第一行的结果
        results = {
            '型号': 'NewModel',
            '保修状态': '有效',
            '查询状态': '成功'
        }
        self.data_manager.update_result(0, results)

        # 验证更新
        assert self.data_manager.df is not None
        row = self.data_manager.df.iloc[0]
        assert row['型号'] == 'NewModel'
        assert row['保修状态'] == '有效'
        assert row['查询状态'] == '成功'

        self.logger.debug.assert_called_with(f"更新行索引 0 的结果: {results}")

    def test_update_result_partial_data(self):
        """测试更新部分查询结果"""
        # 先加载数据
        df = self.data_manager.load_data()
        assert df is not None

        # 只更新部分字段
        results = {
            '型号': 'NewModel',
            '查询状态': '成功'
        }
        self.data_manager.update_result(0, results)

        # 验证更新
        assert self.data_manager.df is not None
        row = self.data_manager.df.iloc[0]
        assert row['型号'] == 'NewModel'
        assert row['保修状态'] is None  # 应该保持原值或为None
        assert row['查询状态'] == '成功'

    def test_update_result_missing_index(self):
        """测试更新不存在的索引"""
        # 先加载数据
        df = self.data_manager.load_data()
        assert df is not None

        results = {'查询状态': '成功'}
        self.data_manager.update_result(999, results)

        # 应该记录警告
        self.logger.warning.assert_called_once_with(f"警告：尝试更新不存在的行索引 999。")

    def test_update_result_no_dataframe(self):
        """测试在没有DataFrame时更新结果"""
        results = {'查询状态': '成功'}
        self.data_manager.update_result(0, results)
        # 应该记录警告
        self.logger.warning.assert_called_once()

    def test_get_unqueried_serial_numbers_success(self):
        """测试成功获取未查询的序列号"""
        # 先加载数据
        df = self.data_manager.load_data()
        assert df is not None

        # 设置查询状态
        assert self.data_manager.df is not None
        self.data_manager.df.at[0, '查询状态'] = '成功'
        self.data_manager.df.at[1, '查询状态'] = '失败'

        unqueried = self.data_manager.get_unqueried_serial_numbers('Serial Number')

        assert len(unqueried) == 1
        assert unqueried[0] == (2, 'SN003')  # 只有第三行未查询

        self.logger.info.assert_called_with("找到 1 个未成功查询的序列号。")

    def test_get_unqueried_serial_numbers_all_queried(self):
        """测试所有序列号都已查询"""
        # 先加载数据
        df = self.data_manager.load_data()
        assert df is not None

        # 设置所有行为成功
        assert self.data_manager.df is not None
        self.data_manager.df['查询状态'] = '成功'

        unqueried = self.data_manager.get_unqueried_serial_numbers('Serial Number')
        assert len(unqueried) == 0
        self.logger.info.assert_called_with("找到 0 个未成功查询的序列号。")

    def test_get_unqueried_serial_numbers_no_dataframe(self):
        """测试在没有DataFrame时获取未查询序列号"""
        unqueried = self.data_manager.get_unqueried_serial_numbers('Serial Number')
        assert unqueried == []
        self.logger.warning.assert_called_once_with("DataFrame 为空，无法获取未查询序列号。")

    def test_get_unqueried_serial_numbers_custom_status_column(self):
        """测试使用自定义状态列名获取未查询序列号"""
        # 先加载数据
        df = self.data_manager.load_data()
        assert df is not None

        # 添加自定义状态列
        assert self.data_manager.df is not None
        self.data_manager.df['Custom Status'] = ['成功', None, '失败']

        unqueried = self.data_manager.get_unqueried_serial_numbers(
            'Serial Number', 'Custom Status'
        )
        assert len(unqueried) == 2  # 第二行（None）和第三行（失败）

    def test_data_manager_with_missing_file(self):
        """测试处理不存在的文件"""
        non_existent_file = os.path.join(self.temp_dir, 'missing.xlsx')
        dm = DataManager(
            file_path=non_existent_file,
            sheet_name='Sheet1',
            sn_column='Serial Number',
            result_columns=self.result_columns,
            logger=self.logger
        )

        df = dm.load_data()
        assert df is None
        assert dm.df is None

    def test_data_manager_integration(self):
        """测试数据管理器的完整工作流程"""
        # 1. 加载数据
        df = self.data_manager.load_data()
        assert df is not None
        assert len(df) == 3

        # 2. 更新结果
        results1 = {'查询状态': '成功', '型号': 'NewModel1'}
        results2 = {'查询状态': '失败', '型号': 'NewModel2'}
        self.data_manager.update_result(0, results1)
        self.data_manager.update_result(1, results2)

        # 3. 获取未查询的序列号
        unqueried = self.data_manager.get_unqueried_serial_numbers('Serial Number')
        assert len(unqueried) == 1
        assert unqueried[0][1] == 'SN003'  # 只有第三个序列号未查询

        # 4. 保存数据
        self.data_manager.save_data()

        # 5. 重新加载验证
        dm2 = DataManager(
            file_path=self.excel_file,
            sheet_name='Sheet1',
            sn_column='Serial Number',
            result_columns=self.result_columns,
            logger=self.logger
        )
        df2 = dm2.load_data()
        assert df2 is not None
        assert df2.at[0, '查询状态'] == '成功'
        assert df2.at[0, '型号'] == 'NewModel1'
        assert df2.at[1, '查询状态'] == '失败'
        assert df2.at[1, '型号'] == 'NewModel2'