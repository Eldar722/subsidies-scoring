import React, { useState } from 'react';

const ValidationForm = ({ onSubmit, isLoading = false, demoFarmers = [] }) => {
  const [formData, setFormData] = useState({
    animal_type: 'КРС_молочное',
    farm_area_hectares: 100,
    livestock_count: 50,
    production_kg_per_head: 220,
    mortality_percent: 0.8,
  });

  const [showDemoOptions, setShowDemoOptions] = useState(false);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]:
        name === 'animal_type' ? value : parseFloat(value) || value,
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const loadDemoFarmer = (farmer) => {
    setFormData({
      animal_type: farmer.animal_type,
      farm_area_hectares: farmer.farm_area_hectares,
      livestock_count: farmer.livestock_count,
      production_kg_per_head: farmer.production_kg_per_head,
      mortality_percent: farmer.mortality_percent,
    });
    setShowDemoOptions(false);
  };

  const animalTypes = [
    'КРС_молочное',
    'КРС_мясное',
    'овца',
    'коза',
    'лошадь',
    'свинья',
    'птица',
  ];

  return (
    <div className="bg-white border rounded-lg p-6 shadow-md">
      <h2 className="text-2xl font-bold mb-6">📋 Заполните данные фермы</h2>

      {/* Demo Farmers Quick Load */}
      {demoFarmers.length > 0 && (
        <div className="mb-6">
          <button
            type="button"
            onClick={() => setShowDemoOptions(!showDemoOptions)}
            className="px-4 py-2 bg-gray-200 hover:bg-gray-300 rounded text-sm font-semibold"
          >
            {showDemoOptions
              ? '✕ Скрыть примеры'
              : '+ Загрузить пример'}
          </button>
          {showDemoOptions && (
            <div className="mt-3 space-y-2">
              {demoFarmers.map((farmer) => (
                <button
                  key={farmer.id}
                  type="button"
                  onClick={() => loadDemoFarmer(farmer)}
                  className="w-full px-4 py-2 bg-blue-100 hover:bg-blue-200 border border-blue-300 rounded text-left text-sm"
                >
                  <div className="font-semibold">{farmer.name}</div>
                  <div className="text-xs text-gray-600">
                    {farmer.livestock_count} голов на {farmer.farm_area_hectares} га
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Animal Type */}
        <div>
          <label className="block text-sm font-semibold mb-2">
            🐄 Тип животного
          </label>
          <select
            name="animal_type"
            value={formData.animal_type}
            onChange={handleChange}
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {animalTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>

        {/* Farm Area */}
        <div>
          <label className="block text-sm font-semibold mb-2">
            🌾 Площадь пастбища (га)
          </label>
          <input
            type="number"
            name="farm_area_hectares"
            value={formData.farm_area_hectares}
            onChange={handleChange}
            min="1"
            step="10"
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Нагрузка: {(formData.livestock_count / formData.farm_area_hectares).toFixed(
              2
            )}{' '}
            ед/га
          </p>
        </div>

        {/* Livestock Count */}
        <div>
          <label className="block text-sm font-semibold mb-2">
            🐑 Поголовье (шт)
          </label>
          <input
            type="number"
            name="livestock_count"
            value={formData.livestock_count}
            onChange={handleChange}
            min="1"
            step="5"
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Production */}
        <div>
          <label className="block text-sm font-semibold mb-2">
            📊 Производство на голову (кг)
          </label>
          <input
            type="number"
            name="production_kg_per_head"
            value={formData.production_kg_per_head}
            onChange={handleChange}
            min="50"
            step="10"
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Минимум для субсидии: 180 кг (для КРС)
          </p>
        </div>

        {/* Mortality */}
        <div>
          <label className="block text-sm font-semibold mb-2">
            ⚠️ Историческая убыль (%)
          </label>
          <input
            type="number"
            name="mortality_percent"
            value={formData.mortality_percent}
            onChange={handleChange}
            min="0"
            max="10"
            step="0.1"
            className="w-full border rounded px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <p className="text-xs text-gray-500 mt-1">
            Норма для КРС: 2.0% - 3.0%
          </p>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isLoading}
          className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-3 rounded transition-colors"
        >
          {isLoading ? '⏳ Проверка...' : '✓ Проверить ферму'}
        </button>
      </form>

      {/* Info */}
      <div className="mt-6 bg-blue-50 border border-blue-200 rounded p-4 text-sm text-gray-700">
        <p>
          💡 <strong>Система проверяет 3 затвора:</strong>
        </p>
        <ul className="list-disc list-inside mt-2 space-y-1 text-xs">
          <li>
            <strong>GATE 1:</strong> Нагрузка на пастбище не превышает норму
          </li>
          <li>
            <strong>GATE 2:</strong> Производство соответствует минимумам
          </li>
          <li>
            <strong>GATE 3:</strong> Убыль животных в пределах нормы
          </li>
        </ul>
      </div>
    </div>
  );
};

export default ValidationForm;
