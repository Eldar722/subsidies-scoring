import React, { useState, useEffect } from 'react';
import ValidationForm from '../components/ValidationForm';
import ValidationResult from '../components/ValidationResult';

const Dashboard = () => {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [demoFarmers, setDemoFarmers] = useState([]);
  const [apiUrl, setApiUrl] = useState(
    localStorage.getItem('apiUrl') || 'http://localhost:8000'
  );

  // Load demo farmers
  useEffect(() => {
    const loadDemoFarmers = async () => {
      try {
        const response = await fetch(`${apiUrl}/api/farmers`);
        if (response.ok) {
          const data = await response.json();
          setDemoFarmers(data);
        }
      } catch (err) {
        console.error('Failed to load demo farmers:', err);
      }
    };

    if (apiUrl) {
      loadDemoFarmers();
    }
  }, [apiUrl]);

  const handleValidate = async (formData) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await fetch(`${apiUrl}/api/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        throw new Error(
          `API error: ${response.status} ${response.statusText}`
        );
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(err.message);
      console.error('Validation error:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-blue-100 p-6">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-blue-900 mb-2">
            🌾 Система Проверки Субсидий
          </h1>
          <p className="text-gray-700">
            Проверьте соответствие вашей фермы требованиям для получения субсидии
          </p>
        </div>

        {/* API URL Selector */}
        <div className="bg-white border rounded-lg p-4 mb-6 shadow-sm">
          <label className="text-sm font-semibold text-gray-700 block mb-2">
            🔗 API URL
          </label>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => {
              setApiUrl(e.target.value);
              localStorage.setItem('apiUrl', e.target.value);
            }}
            className="w-full border rounded px-3 py-2 text-sm"
            placeholder="http://localhost:8000"
          />
        </div>

        {/* Error Display */}
        {error && (
          <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-6 shadow-sm">
            <p className="font-semibold">❌ Ошибка</p>
            <p className="text-sm">{error}</p>
          </div>
        )}

        {/* Main Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Form Section */}
          <div>
            <ValidationForm
              onSubmit={handleValidate}
              isLoading={loading}
              demoFarmers={demoFarmers}
            />
          </div>

          {/* Results Section */}
          <div>
            {result !== null ? (
              <ValidationResult result={result} />
            ) : (
              <div className="bg-white border rounded-lg p-6 shadow-md text-center text-gray-500 h-full flex items-center justify-center">
                <p>👉 Заполните форму и нажмите "Проверить"</p>
              </div>
            )}
          </div>
        </div>

        {/* Info Footer */}
        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="bg-white border rounded-lg p-4 shadow-sm">
            <h3 className="font-semibold text-lg mb-2">🏆 GATE 1: Пастбище</h3>
            <p className="text-sm text-gray-700">
              Нагрузка на пастбище не должна превышать норму более чем на 20%
            </p>
          </div>
          <div className="bg-white border rounded-lg p-4 shadow-sm">
            <h3 className="font-semibold text-lg mb-2">💰 GATE 2: Производство</h3>
            <p className="text-sm text-gray-700">
              Минимальное производство на голову должно быть 180 кг для КРС
            </p>
          </div>
          <div className="bg-white border rounded-lg p-4 shadow-sm">
            <h3 className="font-semibold text-lg mb-2">📊 GATE 3: Убыль</h3>
            <p className="text-sm text-gray-700">
              Естественная убыль не должна превышать 2-3% в зависимости от типа животных
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
