"""
synthetic_data.py — генерация синтетических данных для улучшения ML модели.
Поддерживает SMOTE, Gaussian noise augmentation и bootstrap sampling.
"""

import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from imblearn.over_sampling import SMOTE, BorderlineSMOTE
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline as ImbPipeline
import warnings
warnings.filterwarnings('ignore')


def analyze_class_imbalance(X, y):
    """Анализ дисбаланса классов."""
    unique, counts = np.unique(y, return_counts=True)
    imbalance_ratio = counts.max() / counts.min()
    
    print(f"Классовое распределение:")
    for cls, count in zip(unique, counts):
        print(f"  Класс {cls}: {count} ({count/len(y)*100:.1f}%)")
    print(f"Коэффициент дисбаланса: {imbalance_ratio:.2f}")
    
    return imbalance_ratio


def smote_augmentation(X_train, y_train, sampling_strategy=0.5, random_state=42):
    """
    Применение SMOTE для генерации синтетических примеров minority класса.
    
    Args:
        X_train: обучающие признаки
        y_train: обучающие метки
        sampling_strategy: доля minority класса относительно majority после oversampling
        random_state: seed для воспроизводимости
    
    Returns:
        X_resampled, y_resampled: augmented данные
    """
    print(f"Применение SMOTE с sampling_strategy={sampling_strategy}...")
    
    smote = SMOTE(
        sampling_strategy=sampling_strategy,
        random_state=random_state,
        k_neighbors=5
    )
    
    X_resampled, y_resampled = smote.fit_resample(X_train, y_train)
    
    print(f"Исходный размер: {len(X_train)}")
    print(f"После SMOTE: {len(X_resampled)} (+{len(X_resampled)-len(X_train)} синтетических)")
    print(f"Новое распределение классов: {np.bincount(y_resampled)}")
    
    return X_resampled, y_resampled


def borderline_smote_augmentation(X_train, y_train, sampling_strategy=0.5, random_state=42):
    """
    Borderline-SMOTE фокусируется на примерах рядом с границей решений.
    Полезно когда есть шум в данных.
    """
    print(f"Применение Borderline-SMOTE с sampling_strategy={sampling_strategy}...")
    
    borderline_smote = BorderlineSMOTE(
        sampling_strategy=sampling_strategy,
        random_state=random_state,
        k_neighbors=5
    )
    
    X_resampled, y_resampled = borderline_smote.fit_resample(X_train, y_train)
    
    print(f"Исходный размер: {len(X_train)}")
    print(f"После Borderline-SMOTE: {len(X_resampled)} (+{len(X_resampled)-len(X_train)} синтетических)")
    print(f"Новое распределение классов: {np.bincount(y_resampled)}")
    
    return X_resampled, y_resampled


def gaussian_noise_augmentation(X_train, y_train, noise_factor=0.1, random_state=42):
    """
    Добавление гауссовского шума к числовым признакам для увеличения разнообразия.
    Сохраняет исходные метки.
    
    Args:
        X_train: обучающие признаки (только числовые)
        y_train: обучающие метки
        noise_factor: коэффициент шума (отношение к стандартному отклонению)
        random_state: seed для воспроизводимости
    
    Returns:
        X_augmented, y_augmented: данные с добавленным шумом
    """
    print(f"Применение Gaussian noise augmentation с noise_factor={noise_factor}...")
    
    np.random.seed(random_state)
    
    # Вычисляем стандартное отклонение для каждого признака
    std_dev = X_train.std(axis=0)
    # Избегаем деления на ноль
    std_dev = np.where(std_dev == 0, 1, std_dev)
    
    # Генерируем шум
    noise = np.random.normal(
        loc=0,
        scale=noise_factor * std_dev,
        size=X_train.shape
    )
    
    # Добавляем шум к признакам
    X_augmented = X_train + noise
    
    # Для категориальных признаков оставляем как есть (шум не добавляем)
    # Но в нашем случае все признаки уже числовые после feature engineering
    
    y_augmented = y_train.copy()
    
    print(f"Исходный размер: {len(X_train)}")
    print(f"После Gaussian noise: {len(X_augmented)} (удвоено за счет оригинала + шума)")
    
    # Объединяем оригинал и augmented данные
    X_combined = np.vstack([X_train, X_augmented])
    y_combined = np.hstack([y_train, y_augmented])
    
    print(f"Итоговый размер: {len(X_combined)}")
    print(f"Распределение классов: {np.bincount(y_combined.astype(int))}")
    
    return X_combined, y_combined


def bootstrap_augmentation(X_train, y_train, n_bootstrap=100, random_state=42):
    """
    Bootstrap sampling для создания дополнительных обучающих наборов.
    Полезно для оценки нестабильности модели.
    """
    print(f"Применение bootstrap augmentation с {n_bootstrap} выборками...")
    
    np.random.seed(random_state)
    n_samples = len(X_train)
    
    bootstrap_X = []
    bootstrap_y = []
    
    for i in range(n_bootstrap):
        # Случайная выборка с возвращением
        indices = np.random.choice(n_samples, size=n_samples, replace=True)
        bootstrap_X.append(X_train[indices])
        bootstrap_y.append(y_train[indices])
    
    # Объединяем все bootstrap выборки
    X_bootstrap = np.vstack(bootstrap_X)
    y_bootstrap = np.hstack(bootstrap_y)
    
    print(f"Исходный размер: {len(X_train)}")
    print(f"После bootstrap ({n_bootstrap} выборок): {len(X_bootstrap)}")
    print(f"Распределение классов: {np.bincount(y_bootstrap.astype(int))}")
    
    return X_bootstrap, y_bootstrap


def conditional_generation_vae_style(X_train, y_train, target_class=1, n_samples=None, random_state=42):
    """
    Условная генерация в стиле VAE для конкретного класса.
    Создает новые примеры, условленные на метку класса.
    Упрощенная версия: используем средние и ковариацию класса для генерации.
    """
    if n_samples is None:
        n_samples = len(X_train)
    
    print(f"Условная генерация для класса {target_class} ({n_samples} образцов)...")
    
    np.random.seed(random_state)
    
    # Выбираем только примеры целевого класса
    class_mask = (y_train == target_class)
    X_class = X_train[class_mask]
    
    if len(X_class) < 2:
        print(f"Предупреждение: недостаточно примеров класса {target_class} для генерации")
        return X_train, y_train
    
    # Вычисляем среднее и ковариационную матрицу
    mean_vec = np.mean(X_class, axis=0)
    cov_mat = np.cov(X_class.T)
    
    # Добавляем небольшую диагональ для числовой стабильности
    cov_mat += np.eye(cov_mat.shape[0]) * 1e-6
    
    # Генерируем новые примеры из многомерного нормального распределения
    X_generated = np.random.multivariate_normal(mean_vec, cov_mat, size=n_samples)
    
    # Метки для сгенерированных примеров
    y_generated = np.full(n_samples, target_class)
    
    print(f"Сгенерировано {len(X_generated)} примеров класса {target_class}")
    
    # Объединяем с оригинальными данными
    X_combined = np.vstack([X_train, X_generated])
    y_combined = np.hstack([y_train, y_generated])
    
    return X_combined, y_combined


def create_synthetic_data(X_train, y_train, method='smote', **kwargs):
    """
    Фабричная функция для создания синтетических данных различными методами.
    
    Args:
        X_train: обучающие признаки
        y_train: обучающие метки
        method: метод генерации ('smote', 'borderline_smote', 'gaussian_noise', 
                'bootstrap', 'conditional_vae', 'combined')
        **kwargs: дополнительные параметры для конкретного метода
    
    Returns:
        X_synthetic, y_synthetic: augmented обучающие данные
    """
    print(f"\n{'='*60}")
    print(f"ГЕНЕРАЦИЯ СИНТЕТИЧЕСКИХ ДАННЫХ МЕТОДОМ: {method.upper()}")
    print(f"{'='*60}")
    
    # Анализ исходного дисбаланса
    analyze_class_imbalance(X_train, y_train)
    
    if method == 'smote':
        return smote_augmentation(X_train, y_train, **kwargs)
    elif method == 'borderline_smote':
        return borderline_smote_augmentation(X_train, y_train, **kwargs)
    elif method == 'gaussian_noise':
        return gaussian_noise_augmentation(X_train, y_train, **kwargs)
    elif method == 'bootstrap':
        return bootstrap_augmentation(X_train, y_train, **kwargs)
    elif method == 'conditional_vae':
        return conditional_generation_vae_style(X_train, y_train, **kwargs)
    elif method == 'combined':
        # Комбинируем несколько методов для максимального эффекта
        print("Применение комбинированного подхода...")
        
        # Сначала SMOTE для балансировки классов
        X_smote, y_smote = smote_augmentation(X_train, y_train, 
                                            sampling_strategy=kwargs.get('sampling_strategy', 0.5),
                                            random_state=kwargs.get('random_state', 42))
        
        # Затем добавляем Gaussian noise для увеличения разнообразия
        X_final, y_final = gaussian_noise_augmentation(X_smote, y_smote,
                                                     noise_factor=kwargs.get('noise_factor', 0.05),
                                                     random_state=kwargs.get('random_state', 42))
        
        return X_final, y_final
    else:
        raise ValueError(f"Неподдерживаемый метод: {method}. "
                        f"Доступные методы: smote, borderline_smote, gaussian_noise, bootstrap, conditional_vae, combined")


def save_synthetic_to_supabase(X_synthetic, y_synthetic, feature_names, producers_df=None):
    """
    Подготовка синтетических данных для сохранения в Supabase.
    Добавляет флаг is_synthetic и сохраняет в отдельную таблицу или с флагом.
    """
    print(f"\nПодготовка синтетических данных для Supabase...")
    
    # Создаем DataFrame с синтетическими признаками
    synthetic_df = pd.DataFrame(X_synthetic, columns=feature_names)
    synthetic_df['target'] = y_synthetic
    synthetic_df['is_synthetic'] = True
    
    # Если у нас есть информация о производителях, добавляем её
    if producers_df is not None:
        # Для простоты генерируем случайные producer_id для синтетических данных
        # В реальном сценарии нужно было бы маппить на реальных производителей
        unique_producers = producers_df['producer_id'].unique() if 'producer_id' in producers_df.columns else \
                          [f'SYNTH_{i:06d}' for i in range(len(synthetic_df))]
        
        if len(unique_producers) < len(synthetic_df):
            # Повторяем producer_id если синтетических данных больше
            producer_ids = np.random.choice(unique_producers, size=len(synthetic_df), replace=True)
        else:
            producer_ids = np.random.choice(unique_producers, size=len(synthetic_df), replace=False)
            
        synthetic_df['producer_id'] = producer_ids
        
        # Добавляем другие необходимые колонки со значениями по умолчанию или средними
        for col in ['region', 'direction', 'Наименование субсидирования', 'Район хозяйства']:
            if col in producers_df.columns:
                synthetic_df[col] = np.random.choice(producers_df[col].dropna().unique(), 
                                                   size=len(synthetic_df))
    
    print(f"Подготовлено {len(synthetic_df)} синтетических записей для Supabase")
    print(f"Колонки: {list(synthetic_df.columns)}")
    
    return synthetic_df


if __name__ == "__main__":
    # Тестовый запуск
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from ml.data_loader import load_xlsx
    from ml.feature_engineering import build_features
    
    print("Тестирование генерации синтетических данных...")
    
    # Загружаем и подготавливаем данные
    df = load_xlsx("data/subsidies.xlsx")
    
    # Целевая переменная
    POSITIVE = ["Исполнена"]
    NEGATIVE = ["Отклонена", "Отозвано"]
    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(POSITIVE), "target"] = 1
    df.loc[df["Статус заявки"].isin(NEGATIVE), "target"] = 0
    
    resolved = df.dropna(subset=["target"]).copy()
    resolved["target"] = resolved["target"].astype(int)
    
    # Берем только обучающие данные (2025 год)
    train = resolved[resolved["year"] == 2025].copy()
    
    # Инжиниринг признаков
    X_train = build_features(train, fit=True)
    y_train = train["target"]
    
    print(f"Исходные данные: X={X_train.shape}, y={y_train.shape}")
    
    # Тестируем различные методы генерации
    methods_to_test = ['smote', 'gaussian_noise', 'combined']
    
    for method in methods_to_test:
        print(f"\n{'#'*60}")
        print(f"ТЕСТИРОВАНИЕ МЕТОДА: {method}")
        print(f"{'#'*60}")
        
        # Prepare kwargs based on method
        kwargs = {'random_state': 42}
        if method in ['smote', 'borderline_smote', 'combined']:
            kwargs['sampling_strategy'] = 0.5
        if method in ['gaussian_noise', 'combined']:
            kwargs['noise_factor'] = 0.1
        if method == 'bootstrap':
            kwargs['n_bootstrap'] = 5
        if method == 'conditional_vae':
            kwargs['target_class'] = 1
            kwargs['n_samples'] = 1000
        
        try:
            X_synth, y_synth = create_synthetic_data(
                X_train.values, y_train.values, 
                method=method,
                **kwargs
            )
            
            print(f"Результат: X_synth={X_synth.shape}, y_synth={y_synth.shape}")
            
        except Exception as e:
            print(f"Ошибка при методе {method}: {e}")
    
    print("\nТестирование завершено.")