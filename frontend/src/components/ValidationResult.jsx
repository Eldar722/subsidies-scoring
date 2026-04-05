import React from 'react';

const RiskLevelIndicator = ({ riskLevel, approved }) => {
  const colors = {
    green: 'bg-green-100 border-green-500 text-green-900',
    yellow: 'bg-yellow-100 border-yellow-500 text-yellow-900',
    red: 'bg-red-100 border-red-500 text-red-900',
  };

  const statusText = {
    green: '✅ ОДОБРЕНО',
    yellow: '⚠️ ОДОБРЕНО С РИСКОМ',
    red: '❌ ОТКЛОНЕНО',
  };

  return (
    <div className={`border-2 rounded-lg p-6 mb-4 ${colors[riskLevel] || colors.red}`}>
      <h2 className="text-2xl font-bold mb-2">
        {statusText[riskLevel] || statusText.red}
      </h2>
      {!approved && (
        <p className="text-sm">Не соответствует требованиям для получения субсидии</p>
      )}
    </div>
  );
};

const ValidationResult = ({ result }) => {
  if (!result) {
    return <div className="text-gray-500">Результаты не загружены</div>;
  }

  const {
    approved,
    risk_level,
    reasons,
    subsidy_tenge,
    recommendations,
    detailed_checks,
  } = result;

  const formatCurrency = (value) => {
    if (value === 0) return '0 тн';
    return `${(value / 1_000_000).toFixed(1)} млн тн`;
  };

  return (
    <div className="space-y-6">
      <RiskLevelIndicator riskLevel={risk_level} approved={approved} />

      {/* Результат субсидии */}
      <div className="bg-white border rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-3">💰 Размер субсидии</h3>
        <div className="text-4xl font-bold text-blue-600">
          {formatCurrency(subsidy_tenge)}
        </div>
        {subsidy_tenge > 0 && (
          <p className="text-sm text-gray-600 mt-2">
            На основе производства и штрафов за убыль
          </p>
        )}
      </div>

      {/* Детали проверок */}
      {Object.keys(detailed_checks).length > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-3">🔍 Детали проверок</h3>
          <div className="space-y-3">
            {Object.entries(detailed_checks).map(([key, check]) => (
              <div key={key} className="border-l-4 border-blue-300 pl-4">
                <p className="font-semibold capitalize">{key.replace(/_/g, ' ')}</p>
                <p className="text-sm text-gray-600">
                  Текущее: {check.current ? `${check.current.toFixed(2)}` : check.status}
                </p>
                {check.norm && (
                  <p className="text-sm text-gray-600">
                    Норма: {check.norm.toFixed(2)}
                  </p>
                )}
                {check.ratio && (
                  <p className="text-sm text-gray-600">
                    Процент нормы: {(check.ratio * 100).toFixed(0)}%
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Причины решения */}
      {reasons && reasons.length > 0 && (
        <div className="bg-white border rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-3">📋 Результаты проверок</h3>
          <ul className="space-y-2">
            {reasons.map((reason, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm">
                <span className="mt-1">→</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Рекомендации */}
      {recommendations && recommendations.length > 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="text-lg font-semibold mb-3 text-blue-900">
            💡 Рекомендации
          </h3>
          <ul className="space-y-2">
            {recommendations.map((rec, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-blue-800">
                <span className="font-bold">•</span>
                <span>{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Call to Action */}
      <div className="bg-gray-50 border rounded-lg p-4 text-center">
        {approved ? (
          <p className="text-green-700 font-semibold">
            ✅ Поздравляем! Ваша заявка одобрена для получения субсидии.
          </p>
        ) : (
          <p className="text-red-700 font-semibold">
            ❌ К сожалению, ваша заявка не соответствует требованиям.
            Пожалуйста, воспользуйтесь рекомендациями выше.
          </p>
        )}
      </div>
    </div>
  );
};

export default ValidationResult;
