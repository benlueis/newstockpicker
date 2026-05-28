"""
配置加载器
负责加载和验证YAML配置文件
"""

import yaml
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class ConfigLoader:
    """配置加载器类"""

    def __init__(self, config_dir: str = "config"):
        """
        初始化配置加载器
        
        Args:
            config_dir: 配置文件目录路径
        """
        self.config_dir = Path(config_dir)
        self._config_cache: Dict[str, Any] = {}

    def load_strategies(self) -> Dict[str, Any]:
        """
        加载策略配置
        
        Returns:
            包含所有策略参数的字典
        """
        return self._load_yaml("strategies.yaml")

    def load_pipeline(self) -> Dict[str, Any]:
        """
        加载管道配置
        
        Returns:
            管道配置字典
        """
        return self._load_yaml("pipeline.yaml")

    def _load_yaml(self, filename: str) -> Dict[str, Any]:
        """
        加载YAML文件
        
        Args:
            filename: YAML文件名
            
        Returns:
            解析后的配置字典
        """
        filepath = self.config_dir / filename

        # 检查缓存
        if str(filepath) in self._config_cache:
            return self._config_cache[str(filepath)]

        if not filepath.exists():
            logger.warning(f"配置文件不存在: {filepath}")
            return {}

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config is None:
                    config = {}
                self._config_cache[str(filepath)] = config
                logger.info(f"成功加载配置文件: {filepath}")
                return config
        except Exception as e:
            logger.error(f"加载配置文件失败 {filepath}: {e}")
            return {}

    def get_strategy_params(self, strategy_name: str, preset: str = "default") -> Dict[str, Any]:
        """
        获取特定策略的参数
        
        Args:
            strategy_name: 策略名称 (breakout, dragon_leader, etc.)
            preset: 参数预设 (tight/loose/default)
            
        Returns:
            策略参数字典
        """
        strategies = self.load_strategies()
        if strategy_name in strategies and preset in strategies[strategy_name]:
            return strategies[strategy_name][preset]
        elif strategy_name in strategies and "default" in strategies[strategy_name]:
            # 回退到default预设
            logger.warning(f"策略 {strategy_name} 的 {preset} 预设不存在，使用 default")
            return strategies[strategy_name]["default"]
        else:
            logger.warning(f"策略 {strategy_name} 不存在，返回空参数")
            return {}

    def validate_strategy_params(self, strategy_name: str, params: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        验证策略参数的有效性
        
        Args:
            strategy_name: 策略名称
            params: 要验证的参数字典
            
        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        # 定义参数验证规则
        validation_rules = {
            "breakout": {
                "max_position": (lambda x: 0 < x <= 1, "必须在0-1之间"),
                "max_box_range": (lambda x: 0 < x <= 1, "必须在0-1之间"),
                "min_breakout_pct": (lambda x: x > 0, "必须大于0"),
                "min_vol_ratio": (lambda x: x > 0, "必须大于0"),
                "max_pct_chg": (lambda x: 0 < x <= 20, "必须在0-20之间"),
                "min_amount": (lambda x: x > 0, "必须大于0"),
                "max_upper_shadow_ratio": (lambda x: 0 <= x <= 1, "必须在0-1之间"),
                "min_data_days": (lambda x: x > 0, "必须大于0"),
                "box_days": (lambda x: x > 0, "必须大于0"),
            },
            "dragon_leader": {
                "min_position": (lambda x: 0 < x <= 1, "必须在0-1之间"),
                "min_ret_20d": (lambda x: x > 0, "必须大于0"),
                "max_ret_20d": (lambda x: x > 0, "必须大于0"),
                "max_ret_5d": (lambda x: x > 0, "必须大于0"),
                "min_rs_20d": (lambda x: x > 0, "必须大于0"),
                "min_vol_ratio": (lambda x: x > 0, "必须大于0"),
                "min_pct_chg": (lambda x: x >= 0, "必须大于等于0"),
                "max_pct_chg": (lambda x: 0 < x <= 20, "必须在0-20之间"),
                "min_amount": (lambda x: x > 0, "必须大于0"),
                "top_market": (lambda x: x > 0, "必须大于0"),
                "top_per_industry": (lambda x: x > 0, "必须大于0"),
                "min_leader_score": (lambda x: 0 <= x <= 100, "必须在0-100之间"),
            },
            "sideways_breakout": {
                "lookback_days": (lambda x: x > 0, "必须大于0"),
                "box_days": (lambda x: x > 0, "必须大于0"),
                "max_box_range": (lambda x: x > 1, "必须大于1"),
                "min_breakout_pct": (lambda x: x > 0, "必须大于0"),
                "min_vol_ratio": (lambda x: x > 0, "必须大于0"),
                "max_position_120d": (lambda x: 0 < x <= 1, "必须在0-1之间"),
                "max_pct_chg": (lambda x: 0 < x <= 20, "必须在0-20之间"),
                "min_amount": (lambda x: x > 0, "必须大于0"),
                "max_upper_shadow_ratio": (lambda x: 0 <= x <= 1, "必须在0-1之间"),
                "min_rows": (lambda x: x > 0, "必须大于0"),
            },
            "pullback_ma5": {
                "min_data_days": (lambda x: x > 0, "必须大于0"),
                "min_amount": (lambda x: x > 0, "必须大于0"),
                "max_pct_chg": (lambda x: 0 < x <= 20, "必须在0-20之间"),
                "min_pct_chg": (lambda x: -20 <= x <= 0, "必须在-20到0之间"),
                "trend_confirm_days": (lambda x: x > 0, "必须大于0"),
                "min_days_above_ma5": (lambda x: x > 0, "必须大于0"),
                "min_recent_gain": (lambda x: 0 <= x <= 1, "必须在0-1之间"),
                "max_close_above_ma5_pct": (lambda x: x > 0, "必须大于0"),
                "max_vol_ratio": (lambda x: x > 0, "必须大于0"),
                "min_rebound_ratio": (lambda x: 0 <= x <= 1, "必须在0-1之间"),
            }
        }

        if strategy_name not in validation_rules:
            # 没有定义验证规则的策略，跳过验证
            return True, []

        rules = validation_rules[strategy_name]
        for param_name, (validator, error_msg) in rules.items():
            if param_name in params:
                if not validator(params[param_name]):
                    errors.append(f"{strategy_name}.{param_name}: {error_msg} (当前值: {params[param_name]})")

        return len(errors) == 0, errors

    def reload(self):
        """重新加载所有配置（清除缓存")"""
        self._config_cache.clear()
        logger.info("配置缓存已清除")


# 全局配置加载器实例
config_loader = ConfigLoader()


def load_strategies() -> Dict[str, Any]:
    """便捷函数：加载策略配置"""
    return config_loader.load_strategies()


def load_pipeline() -> Dict[str, Any]:
    """便捷函数：加载管道配置"""
    return config_loader.load_pipeline()


def get_strategy_params(strategy_name: str, preset: str = "default") -> Dict[str, Any]:
    """便捷函数：获取策略参数"""
    return config_loader.get_strategy_params(strategy_name, preset)


def validate_strategy_params(strategy_name: str, params: Dict[str, Any]) -> tuple[bool, list[str]]:
    """便捷函数：验证策略参数"""
    return config_loader.validate_strategy_params(strategy_name, params)


if __name__ == "__main__":
    # 测试配置加载
    logging.basicConfig(level=logging.INFO)

    loader = ConfigLoader()
    print("策略配置:")
    strategies = loader.load_strategies()
    for name, presets in strategies.items():
        print(f"  {name}: {list(presets.keys())}")

    print("\n管道配置:")
    pipeline = loader.load_pipeline()
    print(f"  管道配置键: {list(pipeline.keys())}")

    print("\n获取breakout默认参数:")
    breakout_params = loader.get_strategy_params("breakout", "default")
    for key, value in breakout_params.items():
        print(f"  {key}: {value}")

    print("\n验证breakout默认参数:")
    is_valid, errors = loader.validate_strategy_params("breakout", breakout_params)
    if is_valid:
        print("  参数验证通过")
    else:
        print("  参数验证失败:")
        for error in errors:
            print(f"    - {error}")
