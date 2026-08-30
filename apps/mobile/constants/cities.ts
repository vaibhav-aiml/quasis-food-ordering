// Kept in sync with services/backend/src/tools/swiggy/cities.ts — edit both together if modifying.
export const SUPPORTED_CITIES = [
  'Jaipur',
  'Bengaluru',
  'Mumbai',
  'Delhi NCR',
  'Pune',
  'Hyderabad',
  'Chennai',
  'Kolkata',
  'Ahmedabad',
  'Chandigarh',
  'Lucknow',
  'Indore',
] as const;

export type SupportedCity = typeof SUPPORTED_CITIES[number];
