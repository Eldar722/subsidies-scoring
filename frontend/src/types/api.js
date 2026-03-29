/**
 * @typedef {Object} Producer
 * @property {string} producer_id
 * @property {number} ml_score
 * @property {number} total_applications
 * @property {number} avg_amount
 * @property {string} region
 * @property {string} direction
 * @property {number} delta
 * @property {boolean} hidden_talent
 * @property {number} fcfs_rank
 */

/**
 * @typedef {Object} ShortlistResponse
 * @property {number} total_producers
 * @property {number} optimal_threshold
 * @property {Producer[]} shortlist
 */

/**
 * @typedef {Object} FairnessResponse
 * @property {number} gini_coefficient
 * @property {string} gini_interpretation
 * @property {Array} lorenz_curve
 * @property {Object} kruskal_wallis
 * @property {Array} regions
 * @property {Array} heatmap
 */
