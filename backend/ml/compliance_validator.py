#!/usr/bin/env python3
"""
COMPLIANCE VALIDATOR: 3-Gate System
NORMS_2024 (pasture) → NORMS_2026 (subsidy) → NORMS_2015 (mortality)
"""

from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum

class RiskLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


class ValidationRequest(BaseModel):
    """Farmer data for validation"""
    animal_type: str  # 'КРС', 'овца', 'коза', и т.д.
    farm_area_hectares: float  # площадь пастбища (га)
    livestock_count: int  # поголовье (шт)
    production_kg_per_head: float  # производство на голову (кг)
    mortality_percent: float = 0.0  # историческая убыль (%)


class ValidationResponse(BaseModel):
    """Response with full validation results"""
    approved: bool
    risk_level: RiskLevel
    reasons: List[str]  # что прошло / не прошло
    subsidy_tenge: float  # размер субсидии (тн)
    recommendations: List[str]  # что делать фермеру
    detailed_checks: Dict  # детали каждой проверки


# ═══════════════════════════════════════════════════════════════════════════════════
# NORMS DATABASE (в реальной системе было бы из Supabase)
# ═══════════════════════════════════════════════════════════════════════════════════

# Нормы пастбищной нагрузки (ед/га) по типам животных
NORMS_2024_PASTURE = {
    "КРС": {"spring": 8.0, "summer": 12.0, "winter": 6.0, "default": 8.0},
    "овца": {"spring": 2.0, "summer": 3.0, "winter": 1.5, "default": 2.0},
    "коза": {"spring": 1.8, "summer": 2.5, "winter": 1.2, "default": 1.8},
    "лошадь": {"spring": 1.2, "summer": 1.8, "winter": 0.8, "default": 1.2},
    "свинья": {"spring": 0.5, "summer": 0.7, "winter": 0.3, "default": 0.5},
    "птица": {"spring": 0.1, "summer": 0.15, "winter": 0.05, "default": 0.1},
}

# Нормы субсидирования (тн/кг) и минимальное производство
NORMS_2026_SUBSIDY = {
    "КРС_молочное": {"rate": 190, "min_production": 180},
    "КРС_мясное": {"rate": 175, "min_production": 180},
    "овца": {"rate": 55, "min_production": 100},
    "коза": {"rate": 45, "min_production": 80},
    "лошадь": {"rate": 40, "min_production": 150},
    "свинья": {"rate": 35, "min_production": 120},
    "птица": {"rate": 20, "min_production": 50},
    "верблюд": {"rate": 25, "min_production": 140},
}

# Нормы естественной убыли (%) по возрастам
NORMS_2015_MORTALITY = {
    "КРС": {
        "молодняк_6_12": 1.4,  # молодняк 6-12 месяцев
        "молодняк_12_18": 0.4,  # молодняк 12-18 месяцев
        "взрослый": 3.0,  # маточное поголовье
        "среднее": 2.0,  # усредненная норма
    },
    "овца": {"молодняк": 1.5, "взрослый": 2.0, "среднее": 1.8},
    "коза": {"молодняк": 1.2, "взрослый": 1.8, "среднее": 1.5},
    "лошадь": {"молодняк": 0.8, "взрослый": 1.2, "среднее": 1.0},
    "свинья": {"молодняк": 2.0, "взрослый": 2.5, "среднее": 2.3},
    "птица": {"молодняк": 5.0, "взрослый": 3.0, "среднее": 4.0},
}

# Квартальные нормы (для расчета годовой субсидии)
SUBSIDY_SEASONS = {
    "spring": 1.0,
    "summer": 1.2,  # летом выше (пиковый период)
    "autumn": 1.0,
    "winter": 0.8,  # зимой ниже (сложные условия)
}


class ComplianceValidator:
    """Main validation engine with 3-gate system"""

    @staticmethod
    def get_pasture_norm(animal_type: str, season: str = "default") -> float:
        """Get pasture load norm for animal type"""
        if animal_type not in NORMS_2024_PASTURE:
            raise ValueError(f"Unknown animal type: {animal_type}")
        norms = NORMS_2024_PASTURE[animal_type]
        return norms.get(season, norms["default"])

    @staticmethod
    def get_subsidy_info(animal_type: str) -> Dict:
        """Get subsidy rate and minimum production"""
        if animal_type not in NORMS_2026_SUBSIDY:
            raise ValueError(f"Unknown animal type for subsidy: {animal_type}")
        return NORMS_2026_SUBSIDY[animal_type]

    @staticmethod
    def get_mortality_norm(animal_type: str, age_group: str = "среднее") -> float:
        """Get mortality norm for animal type and age"""
        if animal_type not in NORMS_2015_MORTALITY:
            raise ValueError(f"Unknown animal type for mortality: {animal_type}")
        norms = NORMS_2015_MORTALITY[animal_type]
        return norms.get(age_group, norms["среднее"])

    @staticmethod
    def validate(req: ValidationRequest) -> ValidationResponse:
        """
        Трёхслойная система валидации:
        GATE 1: Пастбищная нагрузка (NORMS_2024)
        GATE 2: Условия субсидирования (NORMS_2026)
        GATE 3: Убыль скота (NORMS_2015)
        """
        reasons = []
        recommendations = []
        detailed_checks = {}
        risk_level = RiskLevel.GREEN
        subsidy_tenge = 0

        # Map animal types to base types for pasture/mortality norms
        # КРС_молочное и КРС_мясное оба используют норм "КРС"
        base_animal_type = req.animal_type.split("_")[0] if "_" in req.animal_type else req.animal_type

        # ═════════════════════════════════════════════════════════════════════════════
        # GATE 1: PASTURE LOAD CHECK (NORMS_2024)
        # ═════════════════════════════════════════════════════════════════════════════
        try:
            pasture_norm = ComplianceValidator.get_pasture_norm(base_animal_type)
            pasture_load = req.livestock_count / req.farm_area_hectares
            pasture_ratio = pasture_load / pasture_norm

            detailed_checks["pasture_load"] = {
                "current": pasture_load,
                "norm": pasture_norm,
                "ratio": pasture_ratio,
                "status": "OK" if pasture_ratio <= 1.0 else "EXCEEDED"
            }

            if pasture_ratio > 1.2:  # Более 20% превышения
                reasons.append(f"❌ Нагрузка на пастбище превышена на {(pasture_ratio - 1) * 100:.0f}%")
                recommendations.append(
                    f"Снизить поголовье с {req.livestock_count} до {int(req.farm_area_hectares * pasture_norm)} голов"
                )
                risk_level = RiskLevel.RED
                return ValidationResponse(
                    approved=False,
                    risk_level=RiskLevel.RED,
                    reasons=reasons,
                    subsidy_tenge=0,
                    recommendations=recommendations,
                    detailed_checks=detailed_checks
                )
            elif pasture_ratio > 0.9:  # Близко к пределу
                reasons.append(f"⚠️ Нагрузка близка к норме (margin: {(1 - pasture_ratio) * 100:.0f}%)")
                recommendations.append("Рассмотрите расширение пастбища")
                risk_level = RiskLevel.YELLOW

        except ValueError as e:
            reasons.append(f"❌ GATE 1 ошибка: {str(e)}")
            return ValidationResponse(
                approved=False,
                risk_level=RiskLevel.RED,
                reasons=reasons,
                subsidy_tenge=0,
                recommendations=recommendations,
                detailed_checks=detailed_checks
            )

        # ═════════════════════════════════════════════════════════════════════════════
        # GATE 2: SUBSIDY CONDITIONS (NORMS_2026)
        # ═════════════════════════════════════════════════════════════════════════════
        try:
            subsidy_info = ComplianceValidator.get_subsidy_info(req.animal_type)
            min_production = subsidy_info["min_production"]
            rate_tenge_per_kg = subsidy_info["rate"]

            detailed_checks["subsidy_conditions"] = {
                "animal_type": req.animal_type,
                "production_kg": req.production_kg_per_head,
                "min_required": min_production,
                "rate_tng_kg": rate_tenge_per_kg,
                "status": "OK" if req.production_kg_per_head >= min_production else "BELOW_MIN"
            }

            if req.production_kg_per_head < min_production:
                reasons.append(f"❌ Производство {req.production_kg_per_head} кг < минимума {min_production} кг")
                recommendations.append(
                    f"Повысить выход на {min_production - req.production_kg_per_head} кг/голову " +
                    "(улучшить кормление +15%, ветконтроль)"
                )
                risk_level = RiskLevel.RED
                return ValidationResponse(
                    approved=False,
                    risk_level=RiskLevel.RED,
                    reasons=reasons,
                    subsidy_tenge=0,
                    recommendations=recommendations,
                    detailed_checks=detailed_checks
                )
            else:
                reasons.append(f"✅ Производство в норме ({req.production_kg_per_head} кг)")

        except ValueError as e:
            reasons.append(f"❌ GATE 2 ошибка: {str(e)}")
            return ValidationResponse(
                approved=False,
                risk_level=RiskLevel.RED,
                reasons=reasons,
                subsidy_tenge=0,
                recommendations=recommendations,
                detailed_checks=detailed_checks
            )

        # ═════════════════════════════════════════════════════════════════════════════
        # GATE 3: MORTALITY CHECK (NORMS_2015)
        # ═════════════════════════════════════════════════════════════════════════════
        try:
            mortality_norm = ComplianceValidator.get_mortality_norm(base_animal_type)

            detailed_checks["mortality"] = {
                "actual": req.mortality_percent,
                "norm": mortality_norm,
                "status": "OK" if req.mortality_percent <= mortality_norm else "EXCEEDED"
            }

            if req.mortality_percent > mortality_norm:
                reasons.append(f"⚠️ Убыль {req.mortality_percent}% > нормы {mortality_norm}%")
                recommendations.append(
                    f"Заболеваемость выше обычного на {req.mortality_percent - mortality_norm:.1f}%. " +
                    "Улучшить ветконтроль и условия содержания"
                )
                # Штраф за убыль но не отказ
                if req.mortality_percent > mortality_norm * 1.5:  # Более чем в 1.5 раза выше
                    risk_level = RiskLevel.YELLOW
            else:
                reasons.append(f"✅ Убыль в норме ({req.mortality_percent}%)")

        except ValueError as e:
            reasons.append(f"⚠️ GATE 3 ошибка: {str(e)} (используем среднее значение)")

        # ═════════════════════════════════════════════════════════════════════════════
        # CALCULATE SUBSIDY
        # ═════════════════════════════════════════════════════════════════════════════
        
        # Получить информацию о субсидии для полного типа (КРС_молочное или КРС_мясное)
        try:
            subsidy_info = ComplianceValidator.get_subsidy_info(req.animal_type)
            rate_tenge_per_kg = subsidy_info["rate"]
        except ValueError:
            # Fallback если полный тип не найден - использовать базовый + default
            subsidy_info = ComplianceValidator.get_subsidy_info(base_animal_type)
            rate_tenge_per_kg = subsidy_info["rate"]
        
        base_subsidy = req.production_kg_per_head * rate_tenge_per_kg

        # Штраф за убыль (пропорциональное снижение)
        mortality_penalty = base_subsidy * (req.mortality_percent / 100) if req.mortality_percent > 0 else 0
        subsidy_tenge = (base_subsidy - mortality_penalty) * 1000  # Convert to tenge

        detailed_checks["subsidy_calculation"] = {
            "base_calculation": f"{req.production_kg_per_head} кг × {rate_tenge_per_kg} тн/кг",
            "base_subsidy": base_subsidy,
            "mortality_penalty": mortality_penalty,
            "final_subsidy_tenge": subsidy_tenge
        }

        if risk_level == RiskLevel.GREEN:
            reasons.append("✅ ВСЕ ПРОВЕРКИ ПРОЙДЕНЫ - СУБСИДИЯ ОДОБРЕНА")
            recommendations.append(
                "Поздравляем! Вы соответствуете всем нормативам. " +
                "Продолжайте поддерживать эту практику."
            )

        return ValidationResponse(
            approved=True,
            risk_level=risk_level,
            reasons=reasons,
            subsidy_tenge=subsidy_tenge,
            recommendations=recommendations,
            detailed_checks=detailed_checks
        )

