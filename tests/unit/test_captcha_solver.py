# -*- coding: utf-8 -*-
"""
验证码识别模块单元测试
"""
import base64
import time
from unittest.mock import patch, MagicMock, Mock
import pytest

import sys
sys.path.insert(0, 'src')

from ruijie_query.captcha.captcha_solver import CaptchaSolver


class TestCaptchaSolver:
    """CaptchaSolver类的单元测试"""

    def setup_method(self):
        """测试方法初始化"""
        self.logger = MagicMock()

        # 模拟验证码配置
        self.captcha_config = {
            'primary_solver': 'ddddocr',
            'enable_ddddocr': True,
            'enable_ai': True,
            'ddddocr_max_attempts': 3
        }

        # 模拟AI设置
        self.ai_settings = {
            'retry_attempts': 3,
            'retry_delay': 5,
            'rate_limit_delay': 30,
            'ai_test_timeout': 120
        }

        # 模拟AI渠道配置
        self.channels = [
            {
                'api_type': 'gemini',
                'api_key': 'test_gemini_key',
                'model_name': 'gemini-pro-vision'
            },
            {
                'api_type': 'openai',
                'api_key': 'test_openai_key',
                'model_name': 'gpt-4-vision-preview'
            }
        ]

    def test_init_with_ddddocr_enabled(self):
        """测试启用ddddocr的初始化"""
        with patch('ddddocr.DdddOcr') as mock_ddddocr:
            mock_instance = MagicMock()
            mock_instance.classification.return_value = 'test123'
            mock_ddddocr.return_value = mock_instance

            solver = CaptchaSolver(
                captcha_config=self.captcha_config,
                ai_settings=self.ai_settings,
                channels=self.channels,
                logger=self.logger
            )

            assert solver.ddddocr_enabled_internal is True
            assert solver.ocr is not None
            self.logger.info.assert_any_call("DdddOcr 初始化成功。")

    def test_init_with_ddddocr_disabled(self):
        """测试禁用ddddocr的初始化"""
        config = self.captcha_config.copy()
        config['enable_ddddocr'] = False

        solver = CaptchaSolver(
            captcha_config=config,
            ai_settings=self.ai_settings,
            channels=self.channels,
            logger=self.logger
        )

        assert solver.ddddocr_enabled_internal is False
        assert solver.ocr is None
        self.logger.info.assert_called_once_with("配置中禁用了 ddddocr。")

    def test_init_with_ddddocr_import_error(self):
        """测试ddddocr导入错误的初始化"""
        config = self.captcha_config.copy()
        config['enable_ddddocr'] = True

        with patch('ddddocr.DdddOcr', side_effect=ImportError("ddddocr not found")):
            solver = CaptchaSolver(
                captcha_config=config,
                ai_settings=self.ai_settings,
                channels=self.channels,
                logger=self.logger
            )

            assert solver.ddddocr_enabled_internal is False
            assert solver.ocr is None
            self.logger.warning.assert_called_once()

    def test_init_with_ddddocr_init_error(self):
        """测试ddddocr初始化错误的初始化"""
        config = self.captcha_config.copy()
        config['enable_ddddocr'] = True

        with patch('ddddocr.DdddOcr', side_effect=Exception("Init failed")):
            solver = CaptchaSolver(
                captcha_config=config,
                ai_settings=self.ai_settings,
                channels=self.channels,
                logger=self.logger
            )

            assert solver.ddddocr_enabled_internal is False
            assert solver.ocr is None
            self.logger.error.assert_called_once()

    def test_solve_with_ddddocr_success(self):
        """测试ddddocr成功识别验证码"""
        with patch('ddddocr.DdddOcr') as mock_ddddocr:
            mock_instance = MagicMock()
            mock_instance.classification.return_value = 'ABCD1234'
            mock_ddddocr.return_value = mock_instance

            solver = CaptchaSolver(
                captcha_config=self.captcha_config,
                ai_settings=self.ai_settings,
                channels=self.channels,
                logger=self.logger
            )

            # 测试图片数据
            test_image_data = b'fake_image_data'

            result = solver._solve_with_ddddocr(test_image_data)

            assert result == 'abcd1234'  # 应该被转为小写并清理
            mock_instance.classification.assert_called_once_with(test_image_data)

    def test_solve_with_ddddocr_failure(self):
        """测试ddddocr识别失败"""
        with patch('ddddocr.DdddOcr') as mock_ddddocr:
            mock_instance = MagicMock()
            mock_instance.classification.side_effect = Exception("识别失败")
            mock_ddddocr.return_value = mock_instance

            solver = CaptchaSolver(
                captcha_config=self.captcha_config,
                ai_settings=self.ai_settings,
                channels=self.channels,
                logger=self.logger
            )

            test_image_data = b'fake_image_data'

            result = solver._solve_with_ddddocr(test_image_data)

            assert result is None
            # 应该记录错误日志
            self.logger.error.assert_called()

    def test_solve_with_ddddocr_not_enabled(self):
        """测试ddddocr未启用时调用"""
        config = self.captcha_config.copy()
        config['enable_ddddocr'] = False

        solver = CaptchaSolver(
            captcha_config=config,
            ai_settings=self.ai_settings,
            channels=self.channels,
            logger=self.logger
        )

        test_image_data = b'fake_image_data'

        result = solver._solve_with_ddddocr(test_image_data)

        assert result is None
        self.logger.warning.assert_called_once_with("Ddddocr 未启用或未成功初始化，跳过识别。")

    def test_solve_captcha_with_ddddocr_success(self):
        """测试使用ddddocr成功解决验证码"""
        with patch('ddddocr.DdddOcr') as mock_ddddocr:
            mock_instance = MagicMock()
            mock_instance.classification.return_value = 'test123'
            mock_ddddocr.return_value = mock_instance

            solver = CaptchaSolver(
                captcha_config=self.captcha_config,
                ai_settings=self.ai_settings,
                channels=self.channels,
                logger=self.logger
            )

            test_image_data = b'fake_image_data'

            result = solver.solve_captcha(test_image_data)

            assert result == 'test123'
            mock_instance.classification.assert_called_once()

    @patch('ruijie_query.captcha.captcha_solver.genai')
    @patch('ruijie_query.captcha.captcha_solver.openai')
    def test_solve_captcha_with_ai_fallback(self, mock_openai, mock_genai):
        """测试ddddocr失败时回退到AI"""
        with patch('ddddocr.DdddOcr') as mock_ddddocr:
            mock_instance = MagicMock()
            mock_instance.classification.side_effect = Exception("ddddocr failed")
            mock_ddddocr.return_value = mock_instance

            # 模拟AI响应
            mock_genai_response = MagicMock()
            mock_genai_response.text = 'AI123'

            mock_genai.configure = MagicMock()
            mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_genai_response

            solver = CaptchaSolver(
                captcha_config=self.captcha_config,
                ai_settings=self.ai_settings,
                channels=self.channels,
                logger=self.logger
            )

            test_image_data = b'fake_image_data'

            result = solver.solve_captcha(test_image_data)

            assert result == 'AI123'

    def test_test_channels_availability_with_no_channels(self):
        """测试没有AI渠道时的可用性测试"""
        solver = CaptchaSolver(
            captcha_config=self.captcha_config,
            ai_settings=self.ai_settings,
            channels=[],  # 空渠道列表
            logger=self.logger
        )

        result = solver.test_channels_availability()

        assert result == []
        self.logger.warning.assert_called_once_with("未配置任何 AI 渠道，跳过 AI 识别。")

    @patch('ruijie_query.captcha.captcha_solver.genai')
    def test_test_channels_availability_with_gemini(self, mock_genai):
        """测试Gemini渠道的可用性测试"""
        channels = [
            {
                'api_type': 'gemini',
                'api_key': 'test_key',
                'model_name': 'gemini-pro-vision'
            }
        ]

        # 模拟成功的Gemini响应
        mock_response = MagicMock()
        mock_response.text = 'test_captcha'
        mock_genai.configure = MagicMock()
        mock_genai.GenerativeModel.return_value.generate_content.return_value = mock_response

        solver = CaptchaSolver(
            captcha_config=self.captcha_config,
            ai_settings=self.ai_settings,
            channels=channels,
            logger=self.logger
        )

        result = solver.test_channels_availability()

        assert len(result) == 1
        assert result[0]['api_type'] == 'gemini'

    def test_test_channels_availability_with_invalid_channel(self):
        """测试无效渠道的可用性测试"""
        channels = [
            {
                'api_type': 'invalid_api',
                'api_key': 'test_key',
                'model_name': 'some_model'
            }
        ]

        solver = CaptchaSolver(
            captcha_config=self.captcha_config,
            ai_settings=self.ai_settings,
            channels=channels,
            logger=self.logger
        )

        result = solver.test_channels_availability()

        assert len(result) == 0

    def test_test_channels_availability_with_no_api_key(self):
        """测试没有API key的渠道测试"""
        channels = [
            {
                'api_type': 'gemini',
                'api_key': None,  # 没有API key
                'model_name': 'gemini-pro-vision'
            }
        ]

        solver = CaptchaSolver(
            captcha_config=self.captcha_config,
            ai_settings=self.ai_settings,
            channels=channels,
            logger=self.logger
        )

        result = solver.test_channels_availability()

        assert len(result) == 0
        # 应该记录警告日志
        self.logger.warning.assert_called()

    @patch('ruijie_query.captcha.captcha_solver.genai', None)
    def test_solve_with_ai_no_library(self):
        """测试AI库未安装时的识别"""
        channels = [
            {
                'api_type': 'gemini',
                'api_key': 'test_key',
                'model_name': 'gemini-pro-vision'
            }
        ]

        solver = CaptchaSolver(
            captcha_config=self.captcha_config,
            ai_settings=self.ai_settings,
            channels=channels,
            logger=self.logger
        )

        test_image_data = b'fake_image_data'

        result = solver._solve_with_ai(test_image_data)

        assert result is None

    def test_parse_ai_response_valid(self):
        """测试解析有效的AI响应"""
        solver = CaptchaSolver(
            captcha_config=self.captcha_config,
            ai_settings=self.ai_settings,
            channels=self.channels,
            logger=self.logger
        )

        # 模拟AI响应
        mock_response = {
            'choices': [
                {
                    'message': {
                        'content': 'ABCD1234'
                    }
                }
            ]
        }

        result = solver._parse_ai_response(mock_response)

        assert result == 'ABCD1234'

    def test_parse_ai_response_invalid(self):
        """测试解析无效的AI响应"""
        solver = CaptchaSolver(
            captcha_config=self.captcha_config,
            ai_settings=self.ai_settings,
            channels=self.channels,
            logger=self.logger
        )

        # 无效的响应格式
        mock_response = {}

        result = solver._parse_ai_response(mock_response)

        assert result is None

    def test_solve_captcha_empty_image(self):
        """测试处理空图片数据"""
        with patch('ddddocr.DdddOcr') as mock_ddddocr:
            mock_instance = MagicMock()
            mock_instance.classification.return_value = ''
            mock_ddddocr.return_value = mock_instance

            solver = CaptchaSolver(
                captcha_config=self.captcha_config,
                ai_settings=self.ai_settings,
                channels=self.channels,
                logger=self.logger
            )

            result = solver.solve_captcha(b'')

            assert result is None

    def test_solve_captcha_all_methods_fail(self):
        """测试所有识别方法都失败的情况"""
        with patch('ddddocr.DdddOcr') as mock_ddddocr:
            mock_instance = MagicMock()
            mock_instance.classification.side_effect = Exception("ddddocr failed")
            mock_ddddocr.return_value = mock_instance

            # 模拟AI也失败
            channels = [
                {
                    'api_type': 'none',  # 跳过AI
                    'api_key': 'test_key'
                }
            ]

            solver = CaptchaSolver(
                captcha_config=self.captcha_config,
                ai_settings=self.ai_settings,
                channels=channels,
                logger=self.logger
            )

            result = solver.solve_captcha(b'fake_image_data')

            assert result is None

    def test_captcha_solver_integration(self):
        """测试验证码识别器的集成场景"""
        with patch('ddddocr.DdddOcr') as mock_ddddocr:
            mock_instance = MagicMock()
            mock_instance.classification.return_value = 'INTEGRATION123'
            mock_ddddocr.return_value = mock_instance

            solver = CaptchaSolver(
                captcha_config=self.captcha_config,
                ai_settings=self.ai_settings,
                channels=self.channels,
                logger=self.logger
            )

            # 1. 测试ddddocr识别
            result1 = solver.solve_captcha(b'test_image_1')
            assert result1 == 'INTEGRATION123'

            # 2. 测试多个识别请求
            result2 = solver.solve_captcha(b'test_image_2')
            assert result2 == 'INTEGRATION123'

            # 验证ddddocr被调用了两次
            assert mock_instance.classification.call_count == 2

    def test_solve_captcha_with_retry_logic(self):
        """测试ddddocr的重试逻辑"""
        with patch('ddddocr.DdddOcr') as mock_ddddocr:
            mock_instance = MagicMock()
            # 前两次失败，第三次成功
            mock_instance.classification.side_effect = [
                Exception("Fail 1"),
                Exception("Fail 2"),
                "FINAL123"
            ]
            mock_ddddocr.return_value = mock_instance

            solver = CaptchaSolver(
                captcha_config=self.captcha_config,
                ai_settings=self.ai_settings,
                channels=self.channels,
                logger=self.logger
            )

            result = solver.solve_captcha(b'test_image')

            assert result == 'final123'  # 应该成功并清理
            assert mock_instance.classification.call_count == 3