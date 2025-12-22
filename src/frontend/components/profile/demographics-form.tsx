'use client';

import { useState, useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { api, UserDemographics } from '@/lib/api';
import { useAuth } from '@/lib/auth';
import {
  UserCircleIcon,
  MagnifyingGlassIcon,
  ChevronDownIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline';

const AGE_RANGES = [
  { value: '', label: 'Select age range' },
  { value: '18-24', label: '18-24' },
  { value: '25-34', label: '25-34' },
  { value: '35-44', label: '35-44' },
  { value: '45-54', label: '45-54' },
  { value: '55-64', label: '55-64' },
  { value: '65+', label: '65+' },
];

const GENDERS = [
  { value: '', label: 'Select gender' },
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'non-binary', label: 'Non-binary' },
  { value: 'other', label: 'Other' },
  { value: 'prefer-not-to-say', label: 'Prefer not to say' },
];

const EDUCATION_LEVELS = [
  { value: '', label: 'Select education level' },
  { value: 'high-school', label: 'High School' },
  { value: 'some-college', label: 'Some College' },
  { value: 'associates', label: "Associate's Degree" },
  { value: 'bachelors', label: "Bachelor's Degree" },
  { value: 'masters', label: "Master's Degree" },
  { value: 'doctorate', label: 'Doctorate' },
  { value: 'professional', label: 'Professional Degree' },
  { value: 'other', label: 'Other' },
];

const EMPLOYMENT_STATUSES = [
  { value: '', label: 'Select employment status' },
  { value: 'employed-full', label: 'Employed Full-time' },
  { value: 'employed-part', label: 'Employed Part-time' },
  { value: 'self-employed', label: 'Self-employed' },
  { value: 'unemployed', label: 'Unemployed' },
  { value: 'student', label: 'Student' },
  { value: 'retired', label: 'Retired' },
  { value: 'homemaker', label: 'Homemaker' },
  { value: 'other', label: 'Other' },
];

const POLITICAL_LEANINGS = [
  { value: '', label: 'Select political leaning' },
  { value: 'very-liberal', label: 'Very Liberal' },
  { value: 'liberal', label: 'Liberal' },
  { value: 'moderate', label: 'Moderate' },
  { value: 'conservative', label: 'Conservative' },
  { value: 'very-conservative', label: 'Very Conservative' },
  { value: 'libertarian', label: 'Libertarian' },
  { value: 'other', label: 'Other' },
  { value: 'prefer-not-to-say', label: 'Prefer not to say' },
];

const MARITAL_STATUSES = [
  { value: '', label: 'Select marital status' },
  { value: 'single', label: 'Single' },
  { value: 'married', label: 'Married' },
  { value: 'domestic-partnership', label: 'Domestic Partnership' },
  { value: 'divorced', label: 'Divorced' },
  { value: 'separated', label: 'Separated' },
  { value: 'widowed', label: 'Widowed' },
  { value: 'prefer-not-to-say', label: 'Prefer not to say' },
];

const RELIGIOUS_AFFILIATIONS = [
  { value: '', label: 'Select religious affiliation' },
  { value: 'christianity', label: 'Christianity' },
  { value: 'islam', label: 'Islam' },
  { value: 'hinduism', label: 'Hinduism' },
  { value: 'buddhism', label: 'Buddhism' },
  { value: 'judaism', label: 'Judaism' },
  { value: 'sikhism', label: 'Sikhism' },
  { value: 'atheist', label: 'Atheist' },
  { value: 'agnostic', label: 'Agnostic' },
  { value: 'spiritual', label: 'Spiritual but not religious' },
  { value: 'other', label: 'Other' },
  { value: 'prefer-not-to-say', label: 'Prefer not to say' },
];

const ETHNICITIES = [
  { value: '', label: 'Select ethnicity' },
  { value: 'white', label: 'White / Caucasian' },
  { value: 'black', label: 'Black / African American' },
  { value: 'hispanic-latino', label: 'Hispanic / Latino' },
  { value: 'asian', label: 'Asian' },
  { value: 'native-american', label: 'Native American / Indigenous' },
  { value: 'pacific-islander', label: 'Pacific Islander' },
  { value: 'middle-eastern', label: 'Middle Eastern / North African' },
  { value: 'mixed', label: 'Mixed / Multiple ethnicities' },
  { value: 'other', label: 'Other' },
  { value: 'prefer-not-to-say', label: 'Prefer not to say' },
];

const HOUSEHOLD_INCOMES = [
  { value: '', label: 'Select household income' },
  { value: 'under-25k', label: 'Under $25,000' },
  { value: '25k-50k', label: '$25,000 - $49,999' },
  { value: '50k-75k', label: '$50,000 - $74,999' },
  { value: '75k-100k', label: '$75,000 - $99,999' },
  { value: '100k-150k', label: '$100,000 - $149,999' },
  { value: '150k-200k', label: '$150,000 - $199,999' },
  { value: 'over-200k', label: '$200,000+' },
  { value: 'prefer-not-to-say', label: 'Prefer not to say' },
];

const PARENTAL_STATUSES = [
  { value: '', label: 'Select parental status' },
  { value: 'no-children', label: 'No children' },
  { value: 'expecting', label: 'Expecting' },
  { value: 'parent-young', label: 'Parent (children under 18)' },
  { value: 'parent-adult', label: 'Parent (adult children)' },
  { value: 'guardian', label: 'Guardian / Foster parent' },
  { value: 'prefer-not-to-say', label: 'Prefer not to say' },
];

const HOUSING_STATUSES = [
  { value: '', label: 'Select housing status' },
  { value: 'own', label: 'Own' },
  { value: 'rent', label: 'Rent' },
  { value: 'live-with-family', label: 'Live with family' },
  { value: 'student-housing', label: 'Student housing' },
  { value: 'other', label: 'Other' },
  { value: 'prefer-not-to-say', label: 'Prefer not to say' },
];

const POINTS_MAP: Record<string, number> = {
  age_range: 150,
  gender: 100,
  country: 150,
  region: 100,
  state_province: 125,
  city: 100,
  education_level: 150,
  employment_status: 125,
  industry: 125,
  political_leaning: 200,
  // New fields
  marital_status: 125,
  religious_affiliation: 175,
  ethnicity: 175,
  household_income: 200,
  parental_status: 100,
  housing_status: 100,
};

interface SearchableDropdownProps {
  label: string;
  value: string;
  placeholder: string;
  items: { value: string; label: string }[];
  onChange: (value: string) => void;
  onSearch?: (search: string) => void;
  isLoading?: boolean;
  disabled?: boolean;
  points?: number;
}

function SearchableDropdown({
  label,
  value,
  placeholder,
  items,
  onChange,
  onSearch,
  isLoading,
  disabled,
  points,
}: SearchableDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [search, setSearch] = useState('');
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  useEffect(() => {
    if (onSearch) {
      const timer = setTimeout(() => onSearch(search), 300);
      return () => clearTimeout(timer);
    }
  }, [search, onSearch]);

  const filteredItems = items.filter(item =>
    item.label.toLowerCase().includes(search.toLowerCase())
  );

  const selectedLabel = items.find(item => item.value === value)?.label || value;

  return (
    <div ref={dropdownRef} className="relative">
      <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
        <span>{label}</span>
        {points && points > 0 && (
          <span className="text-xs text-primary-600 dark:text-cyan-400">+{points} pts</span>
        )}
      </label>
      <div className="relative">
        <div
          onClick={() => !disabled && setIsOpen(!isOpen)}
          className={`w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white cursor-pointer flex items-center justify-between focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50 ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
        >
          <span className={value ? 'text-gray-900 dark:text-white' : 'text-gray-500 dark:text-slate-500'}>
            {value ? selectedLabel : placeholder}
          </span>
          <div className="flex items-center gap-2">
            {value && !disabled && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onChange('');
                  setSearch('');
                }}
                className="text-gray-400 dark:text-slate-400 hover:text-gray-600 dark:hover:text-white"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            )}
            <ChevronDownIcon className={`h-4 w-4 text-gray-400 dark:text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
          </div>
        </div>

        {isOpen && !disabled && (
          <div className="absolute z-50 mt-1 w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-xl max-h-64 overflow-hidden">
            <div className="p-2 border-b border-gray-200 dark:border-slate-700">
              <div className="relative">
                <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400 dark:text-slate-400" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search..."
                  className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-600 rounded-lg pl-9 pr-4 py-2 text-sm text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
                  autoFocus
                />
              </div>
            </div>
            <div className="overflow-y-auto max-h-48">
              {isLoading ? (
                <div className="px-4 py-3 text-sm text-gray-500 dark:text-slate-400">Loading...</div>
              ) : filteredItems.length === 0 ? (
                <div className="px-4 py-3 text-sm text-gray-500 dark:text-slate-400">No results found</div>
              ) : (
                filteredItems.map(item => (
                  <button
                    key={item.value}
                    type="button"
                    onClick={() => {
                      onChange(item.value);
                      setIsOpen(false);
                      setSearch('');
                    }}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 dark:hover:bg-slate-700/50 transition-colors ${
                      value === item.value ? 'bg-primary-100 dark:bg-cyan-500/20 text-primary-600 dark:text-cyan-400' : 'text-gray-900 dark:text-white'
                    }`}
                  >
                    {item.label}
                  </button>
                ))
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

interface DemographicsFormProps {
  onUpdate?: () => void;
}

export function DemographicsForm({ onUpdate }: DemographicsFormProps) {
  const queryClient = useQueryClient();
  const { refreshUser } = useAuth();
  const [formData, setFormData] = useState<UserDemographics>({});
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [selectedCountryCode, setSelectedCountryCode] = useState<string>('');
  const [selectedStateId, setSelectedStateId] = useState<number | null>(null);

  // Fetch demographics
  const { data: demographics, isLoading: demographicsLoading } = useQuery({
    queryKey: ['demographics'],
    queryFn: () => api.getDemographics(),
  });

  // Fetch countries
  const { data: countries, isLoading: countriesLoading } = useQuery({
    queryKey: ['countries'],
    queryFn: () => api.getCountries(),
  });

  // Fetch states based on selected country
  const { data: states, isLoading: statesLoading } = useQuery({
    queryKey: ['states', selectedCountryCode],
    queryFn: () => api.getStatesByCountry(selectedCountryCode),
    enabled: !!selectedCountryCode,
  });

  // Fetch cities based on selected state
  const { data: cities, isLoading: citiesLoading } = useQuery({
    queryKey: ['cities', selectedStateId],
    queryFn: () => api.getCitiesByState(selectedStateId!),
    enabled: !!selectedStateId,
  });

  // Initialize form and country/state selections when demographics load
  useEffect(() => {
    if (demographics) {
      setFormData(demographics);
      // The country field stores the ISO code - use it directly
      if (demographics.country) {
        setSelectedCountryCode(demographics.country);
      }
    }
  }, [demographics]);

  // Find state ID when states load and we have a state_province name
  useEffect(() => {
    if (demographics?.state_province && states) {
      const state = states.find(s => s.name === demographics.state_province);
      if (state) {
        setSelectedStateId(state.id);
      }
    }
  }, [demographics?.state_province, states]);

  const updateMutation = useMutation({
    mutationFn: (data: UserDemographics) => api.updateDemographics(data),
    onSuccess: (response) => {
      queryClient.invalidateQueries({ queryKey: ['demographics'] });
      queryClient.invalidateQueries({ queryKey: ['profile'] });
      queryClient.invalidateQueries({ queryKey: ['achievements'] });
      setSuccessMessage(response.message);
      setTimeout(() => setSuccessMessage(null), 5000);
      // Refresh user in auth context to update nav bar points
      refreshUser();
      onUpdate?.();
    },
  });

  const handleChange = (field: keyof UserDemographics, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value || undefined }));
  };

  const handleCountryChange = (countryCode: string) => {
    // Store the country code in formData (DB expects ISO code)
    handleChange('country', countryCode);
    setSelectedCountryCode(countryCode);
    // Clear state and city when country changes
    handleChange('state_province', '');
    handleChange('city', '');
    setSelectedStateId(null);
  };

  const handleStateChange = (stateName: string) => {
    handleChange('state_province', stateName);
    // Find state ID
    const state = states?.find(s => s.name === stateName);
    setSelectedStateId(state?.id || null);
    // Clear city when state changes
    handleChange('city', '');
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    updateMutation.mutate(formData);
  };

  const getFieldPoints = (field: keyof UserDemographics) => {
    const currentValue = demographics?.[field];
    const newValue = formData[field];
    if (!currentValue && newValue) {
      return POINTS_MAP[field] || 0;
    }
    return 0;
  };

  const totalPotentialPoints = Object.keys(POINTS_MAP).reduce((sum, field) => {
    const key = field as keyof UserDemographics;
    if (!demographics?.[key]) {
      return sum + (POINTS_MAP[field] || 0);
    }
    return sum;
  }, 0);

  // Convert API data to dropdown format
  // Country uses code as value but displays name
  const countryItems = (countries || []).map(c => ({ value: c.code, label: c.name }));
  const stateItems = (states || []).map(s => ({ value: s.name, label: s.name }));
  const cityItems = (cities || []).map(c => ({ value: c.name, label: c.name }));

  if (demographicsLoading) {
    return (
      <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 dark:bg-slate-700 rounded w-1/3"></div>
          <div className="h-10 bg-gray-200 dark:bg-slate-700 rounded"></div>
          <div className="h-10 bg-gray-200 dark:bg-slate-700 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-slate-800/50 rounded-xl border border-gray-200 dark:border-slate-700/50 p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 bg-primary-100 dark:bg-cyan-500/20 rounded-lg">
          <UserCircleIcon className="h-6 w-6 text-primary-600 dark:text-cyan-400" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Demographics</h3>
          <p className="text-sm text-gray-600 dark:text-slate-400">
            Share your info to improve poll insights
            {totalPotentialPoints > 0 && (
              <span className="text-primary-600 dark:text-cyan-400 ml-2">
                (up to {totalPotentialPoints} points available!)
              </span>
            )}
          </p>
        </div>
      </div>

      {successMessage && (
        <div className="mb-4 p-3 bg-green-100 dark:bg-green-500/20 border border-green-300 dark:border-green-500/30 rounded-lg text-green-700 dark:text-green-400 text-sm">
          {successMessage}
        </div>
      )}

      {updateMutation.isError && (
        <div className="mb-4 p-3 bg-red-100 dark:bg-red-500/20 border border-red-300 dark:border-red-500/30 rounded-lg text-red-700 dark:text-red-400 text-sm">
          Failed to update demographics. Please try again.
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Age Range */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Age Range</span>
            {getFieldPoints('age_range') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('age_range')} pts</span>
            )}
          </label>
          <select
            value={formData.age_range || ''}
            onChange={(e) => handleChange('age_range', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {AGE_RANGES.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Gender */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Gender</span>
            {getFieldPoints('gender') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('gender')} pts</span>
            )}
          </label>
          <select
            value={formData.gender || ''}
            onChange={(e) => handleChange('gender', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {GENDERS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Country - Searchable */}
        <SearchableDropdown
          label="Country"
          value={formData.country || ''}
          placeholder="Select your country"
          items={countryItems}
          onChange={handleCountryChange}
          isLoading={countriesLoading}
          points={getFieldPoints('country')}
        />

        {/* State/Province - Searchable (dependent on country) */}
        <SearchableDropdown
          label="State/Province"
          value={formData.state_province || ''}
          placeholder={selectedCountryCode ? "Select your state/province" : "Select a country first"}
          items={stateItems}
          onChange={handleStateChange}
          isLoading={statesLoading}
          disabled={!selectedCountryCode}
          points={getFieldPoints('state_province')}
        />

        {/* City - Searchable (dependent on state) */}
        <SearchableDropdown
          label="City"
          value={formData.city || ''}
          placeholder={selectedStateId ? "Select your city" : "Select a state/province first"}
          items={cityItems}
          onChange={(value) => handleChange('city', value)}
          isLoading={citiesLoading}
          disabled={!selectedStateId}
          points={getFieldPoints('city')}
        />

        {/* Education Level */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Education Level</span>
            {getFieldPoints('education_level') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('education_level')} pts</span>
            )}
          </label>
          <select
            value={formData.education_level || ''}
            onChange={(e) => handleChange('education_level', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {EDUCATION_LEVELS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Employment Status */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Employment Status</span>
            {getFieldPoints('employment_status') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('employment_status')} pts</span>
            )}
          </label>
          <select
            value={formData.employment_status || ''}
            onChange={(e) => handleChange('employment_status', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {EMPLOYMENT_STATUSES.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Industry */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Industry</span>
            {getFieldPoints('industry') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('industry')} pts</span>
            )}
          </label>
          <input
            type="text"
            value={formData.industry || ''}
            onChange={(e) => handleChange('industry', e.target.value)}
            placeholder="Enter your industry"
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-slate-500 focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          />
        </div>

        {/* Political Leaning */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Political Leaning</span>
            {getFieldPoints('political_leaning') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('political_leaning')} pts</span>
            )}
          </label>
          <select
            value={formData.political_leaning || ''}
            onChange={(e) => handleChange('political_leaning', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {POLITICAL_LEANINGS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Marital Status */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Marital Status</span>
            {getFieldPoints('marital_status') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('marital_status')} pts</span>
            )}
          </label>
          <select
            value={formData.marital_status || ''}
            onChange={(e) => handleChange('marital_status', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {MARITAL_STATUSES.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Religious Affiliation */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Religious Affiliation</span>
            {getFieldPoints('religious_affiliation') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('religious_affiliation')} pts</span>
            )}
          </label>
          <select
            value={formData.religious_affiliation || ''}
            onChange={(e) => handleChange('religious_affiliation', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {RELIGIOUS_AFFILIATIONS.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Ethnicity */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Ethnicity</span>
            {getFieldPoints('ethnicity') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('ethnicity')} pts</span>
            )}
          </label>
          <select
            value={formData.ethnicity || ''}
            onChange={(e) => handleChange('ethnicity', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {ETHNICITIES.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Household Income */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Household Income</span>
            {getFieldPoints('household_income') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('household_income')} pts</span>
            )}
          </label>
          <select
            value={formData.household_income || ''}
            onChange={(e) => handleChange('household_income', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {HOUSEHOLD_INCOMES.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Parental Status */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Parental Status</span>
            {getFieldPoints('parental_status') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('parental_status')} pts</span>
            )}
          </label>
          <select
            value={formData.parental_status || ''}
            onChange={(e) => handleChange('parental_status', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {PARENTAL_STATUSES.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        {/* Housing Status */}
        <div>
          <label className="flex items-center justify-between text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            <span>Housing Status</span>
            {getFieldPoints('housing_status') > 0 && (
              <span className="text-xs text-primary-600 dark:text-cyan-400">+{getFieldPoints('housing_status')} pts</span>
            )}
          </label>
          <select
            value={formData.housing_status || ''}
            onChange={(e) => handleChange('housing_status', e.target.value)}
            className="w-full bg-gray-50 dark:bg-slate-900/50 border border-gray-300 dark:border-slate-700 rounded-lg px-4 py-2.5 text-gray-900 dark:text-white focus:outline-hidden focus:ring-2 focus:ring-primary-500/50 dark:focus:ring-cyan-500/50"
          >
            {HOUSING_STATUSES.map(opt => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>

        <button
          type="submit"
          disabled={updateMutation.isPending}
          className="w-full bg-linear-to-r from-primary-500 to-accent-500 dark:from-cyan-500 dark:to-blue-500 text-white font-medium py-2.5 rounded-lg hover:from-primary-600 hover:to-accent-600 dark:hover:from-cyan-600 dark:hover:to-blue-600 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {updateMutation.isPending ? 'Saving...' : 'Save Demographics'}
        </button>
      </form>
    </div>
  );
}
