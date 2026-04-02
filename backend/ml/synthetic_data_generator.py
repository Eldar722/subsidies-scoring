"""
synthetic_data_generator.py — генерация синтетических данных для улучшения модели.

Используёт три подхода (можно комбинировать):
1. Borderline-SMOTE — синтетика для меньшинства класса (граничные случаи)
2. Gaussian noise augmentation — добавление шума к реальным данным
3. Bootstrap sampling — bootstrap с заменой для увеличения diversity

Все методы сохраняют статистику реального датасета.
"""

import pandas as pd
import numpy as np
from sklearn.neighbors import NearestNeighbors
from typing import Tuple, List
import warnings
warnings.filterwarnings("ignore")


class SyntheticDataGenerator:
    """Генератор синтетических данных для ML pipeline."""
    
    def __init__(self, random_state: int = 42):
        self.random_state = random_state
        np.random.seed(random_state)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Borderline-SMOTE
    # ═══════════════════════════════════════════════════════════════════════════
    
    def borderline_smote(self, 
                        X_numeric: np.ndarray,
                        y: np.ndarray,
                        k_neighbors: int = 5,
                        sampling_ratio: float = 0.5) -> Tuple[np.ndarray, np.ndarray]:
        """Borderline-SMOTE: генерирует синтетику для меньшинства класса.
        
        Принцип: находит "граничные" точки меньшинства (те, у которых соседи из 
        большинства класса) и создает синтетику между ними и их соседями.
        
        Args:
            X_numeric: (n_samples, n_features) числовыe признаки, нормализованные
            y: (n_samples,) целевой переменный
            k_neighbors: кол-во соседей для поиска
            sampling_ratio: доля синтетики относительно меньшинства
        
        Returns:
            (X_synthetic, y_synthetic)
        """
        # Определить класс большинства и меньшинства
        unique_classes, counts = np.unique(y, return_counts=True)
        if len(unique_classes) != 2:
            raise ValueError("Поддерживается только binary classification")
        
        minority_class = unique_classes[np.argmin(counts)]
        majority_class = unique_classes[np.argmax(counts)]
        
        # Разделить данные
        X_minority = X_numeric[y == minority_class]
        X_majority = X_numeric[y == majority_class]
        
        # Найти "граничные" примеры меньшинства
        # Граничными считаются те, у которых в k соседях >= 50% большинства
        nbrs_all = NearestNeighbors(n_neighbors=k_neighbors + 1).fit(X_numeric)
        distances, indices = nbrs_all.kneighbors(X_minority)
        
        is_borderline = []
        for sample_idx, neighbor_indices in enumerate(indices):
            # исключить сам образец (индекс 0)
            neighbor_classes = y[neighbor_indices[1:]]
            majority_count = np.sum(neighbor_classes == majority_class)
            
            # Граничный, если тут меньшинство + 50% большинства
            is_borderline.append(majority_count >= k_neighbors // 2)
        
        X_borderline = X_minority[is_borderline]
        
        if len(X_borderline) == 0:
            print("[WARN] No borderline samples found, using all minority instead")
            X_borderline = X_minority
        
        # Генерировать синтетику
        n_synthetic = max(1, int(len(X_borderline) * sampling_ratio))
        X_synthetic = []
        
        for _ in range(n_synthetic):
            # Выбрать random граничный пример и его k-ый сосед из others
            idx = np.random.randint(len(X_borderline))
            sample = X_borderline[idx]
            
            # Найти k-ый сосед этого граничного примера
            neighbors = NearestNeighbors(n_neighbors=k_neighbors + 1).fit(X_numeric)
            _, neighbor_idxs = neighbors.kneighbors([sample])
            
            # Выбрать random сосед
            neighbor_idx = neighbor_idxs[0, np.random.randint(1, len(neighbor_idxs[0]))]
            neighbor = X_numeric[neighbor_idx]
            
            # Линейная интерполяция между sample и neighbor
            alpha = np.random.uniform(0, 1)
            synthetic = sample + alpha * (neighbor - sample)
            X_synthetic.append(synthetic)
        
        X_synthetic = np.array(X_synthetic)
        y_synthetic = np.full(len(X_synthetic), minority_class)
        
        return X_synthetic, y_synthetic
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Gaussian Noise Augmentation
    # ═══════════════════════════════════════════════════════════════════════════
    
    def gaussian_augmentation(self,
                             X_numeric: np.ndarray,
                             y: np.ndarray,
                             noise_std_ratio: float = 0.05,
                             n_augment_ratio: float = 0.3) -> Tuple[np.ndarray, np.ndarray]:
        """Добавить gaussian шум к реальным данным.
        
        Это консервативный подход: добавляем шум, пропорциональный std каждого 
        признака, чтобы создать близких "двойников" реальных примеров.
        
        Args:
            X_numeric: (n_samples, n_features)
            y: (n_samples,)
            noise_std_ratio: отношение шума к std признака (0.05 = 5%)
            n_augment_ratio: доля синтетики относительно оригинала
        
        Returns:
            (X_synthetic, y_synthetic)
        """
        n_synthetic = max(1, int(len(X_numeric) * n_augment_ratio))
        
        # Вычислить std для каждого признака
        feature_stds = np.std(X_numeric, axis=0, ddof=1)
        feature_stds = np.where(feature_stds > 0, feature_stds, 1.0)  #避免除以0
        
        X_synthetic = []
        y_synthetic = []
        
        for _ in range(n_synthetic):
            # Выбрать random оригинальный sample
            idx = np.random.randint(len(X_numeric))
            sample = X_numeric[idx]
            
            # Добавить gaussian шум, пропорциональный std признака
            noise = np.random.normal(0, 1, sample.shape)
            noise = noise * (feature_stds * noise_std_ratio)
            
            synthetic = sample + noise
            X_synthetic.append(synthetic)
            y_synthetic.append(y[idx])
        
        return np.array(X_synthetic), np.array(y_synthetic)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Bootstrap Sampling
    # ═══════════════════════════════════════════════════════════════════════════
    
    def bootstrap_sampling(self,
                          X_numeric: np.ndarray,
                          y: np.ndarray,
                          n_bootstrap_ratio: float = 0.3) -> Tuple[np.ndarray, np.ndarray]:
        """Bootstrap sampling: выборка с заменой для увеличения diversity.
        
        Args:
            X_numeric: (n_samples, n_features)
            y: (n_samples,)
            n_bootstrap_ratio: какую долю от оригинального датасета добавить
        
        Returns:
            (X_synthetic, y_synthetic)
        """
        n_bootstrap = max(1, int(len(X_numeric) * n_bootstrap_ratio))
        
        # Выборка с заменой
        indices = np.random.choice(len(X_numeric), size=n_bootstrap, replace=True)
        
        X_synthetic = X_numeric[indices]
        y_synthetic = y[indices]
        
        return X_synthetic, y_synthetic


def generate_synthetic_training_data(df_train: pd.DataFrame,
                                     numeric_features: List[str],
                                     cat_features: List[str],
                                     methods: List[str] = None,
                                     verbose: bool = True) -> pd.DataFrame:
    """Главная функция: генерировать синтетические данные для train.
    
    Используется комбинация методов для максимального эффекта.
    
    Args:
        df_train: DataFrame с train данными (должен содержать 'target')
        numeric_features: список числовых признаков
        cat_features: список категориальных признаков
        methods: какие методы использовать ['borderline_smote', 'gaussian', 'bootstrap']
        verbose: выводить ли прогресс
    
    Returns:
        pd.DataFrame с синтетическими данными (того же формата)
    """
    if methods is None:
        methods = ["borderline_smote", "gaussian", "bootstrap"]
    
    df_train = df_train.copy()
    
    # === Нормализовать числовые признаки ===
    X_numeric_raw = df_train[numeric_features].fillna(0).values
    
    # Min-Max нормализация для SMOTE (нужны bounded значения)
    from sklearn.preprocessing import MinMaxScaler
    scaler = MinMaxScaler()
    X_numeric = scaler.fit_transform(X_numeric_raw)
    
    y = df_train["target"].values
    
    # === Генерировать синтетику ===
    gen = SyntheticDataGenerator()
    synthetic_dfs = []
    
    if "borderline_smote" in methods:
        if verbose:
            print("[*] Borderline-SMOTE...")
        try:
            X_syn, y_syn = gen.borderline_smote(X_numeric, y, sampling_ratio=0.5)  # noqa
            # Денормализовать
            X_syn_raw = scaler.inverse_transform(X_syn)
            
            df_syn = pd.DataFrame(X_syn_raw, columns=numeric_features)
            df_syn["target"] = y_syn
            
            # Для категориальных признаков: случайно выбрать из train
            for cat in cat_features:
                df_syn[cat] = np.random.choice(df_train[cat].dropna().values, 
                                               size=len(df_syn), replace=True)
            
            synthetic_dfs.append(df_syn)
            if verbose:
                print(f"   Generated {len(df_syn)} borderline-SMOTE samples")
        except Exception as e:
            print(f"[WARN] Borderline-SMOTE failed: {e}")
    
    if "gaussian" in methods:
        if verbose:
            print("[*] Gaussian augmentation...")
        X_syn, y_syn = gen.gaussian_augmentation(X_numeric, y, noise_std_ratio=0.05, 
                                                 n_augment_ratio=0.3)
        X_syn_raw = scaler.inverse_transform(X_syn)
        
        df_syn = pd.DataFrame(X_syn_raw, columns=numeric_features)
        df_syn["target"] = y_syn
        
        for cat in cat_features:
            df_syn[cat] = np.random.choice(df_train[cat].dropna().values, 
                                           size=len(df_syn), replace=True)
        
        synthetic_dfs.append(df_syn)
        if verbose:
            print(f"   Generated {len(df_syn)} Gaussian samples")
    
    if "bootstrap" in methods:
        if verbose:
            print("[*] Bootstrap sampling...")
        X_syn, y_syn = gen.bootstrap_sampling(X_numeric, y, n_bootstrap_ratio=0.2)
        X_syn_raw = scaler.inverse_transform(X_syn)
        
        df_syn = pd.DataFrame(X_syn_raw, columns=numeric_features)
        df_syn["target"] = y_syn
        
        for cat in cat_features:
            df_syn[cat] = np.random.choice(df_train[cat].dropna().values, 
                                           size=len(df_syn), replace=True)
        
        synthetic_dfs.append(df_syn)
        if verbose:
            print(f"   Generated {len(df_syn)} bootstrap samples")
    
    # === Объединить все синтетические данные ===
    if synthetic_dfs:
        df_synthetic_all = pd.concat(synthetic_dfs, ignore_index=True)
        if verbose:
            print(f"\n✓ Total synthetic samples: {len(df_synthetic_all)}")
            print(f"  Synthetic positive rate: {df_synthetic_all['target'].mean():.1%}")
            print(f"  Original positive rate: {df_train['target'].mean():.1%}")
        return df_synthetic_all
    else:
        return pd.DataFrame()


if __name__ == "__main__":
    from ml.data_loader import load_xlsx
    
    df = load_xlsx()
    df["target"] = np.nan
    df.loc[df["Статус заявки"].isin(["Исполнена"]), "target"] = 1
    df.loc[df["Статус заявки"].isin(["Отклонена", "Отозвано"]), "target"] = 0
    
    train_df = df[df["year"] == 2025].dropna(subset=["target"]).copy()
    train_df["target"] = train_df["target"].astype(int)
    
    numeric_features = [
        "month", "hour", "day_of_year", "day_of_week",
        "Норматив", "Причитающая сумма"
    ]
    cat_features = ["Область", "Направление водства", "Наименование субсидирования"]
    
    print(f"Original train size: {len(train_df)}")
    print(f"Original positive rate: {train_df['target'].mean():.1%}\n")
    
    df_synthetic = generate_synthetic_training_data(
        train_df, numeric_features, cat_features, 
        methods=["borderline_smote", "gaussian", "bootstrap"],
        verbose=True
    )
