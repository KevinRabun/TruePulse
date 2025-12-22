/**
 * API Client for TruePulse Backend
 */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
const FRONTEND_API_SECRET = process.env.NEXT_PUBLIC_FRONTEND_API_SECRET || 'truepulse-frontend-secret-change-in-production';

// Types
export type PollStatus = 'scheduled' | 'active' | 'closed' | 'archived';
export type PollType = 'pulse' | 'flash' | 'standard';

export interface Poll {
  id: string;
  question: string;
  choices: PollChoice[];
  category: string;
  source_event: string;
  status: PollStatus;
  created_at: string;
  expires_at: string;
  scheduled_start?: string;
  scheduled_end?: string;
  is_active: boolean;
  is_special: boolean;
  duration_hours: number;
  total_votes: number;
  ai_generated: boolean;
  poll_type?: PollType;
  time_remaining_seconds?: number;
}

export interface PollWithResults extends Poll {
  choices: PollChoiceWithResults[];
  confidence_interval?: number;
  demographic_breakdown?: Record<string, Record<string, number>>;
}

export interface PollChoice {
  id: string;
  text: string;
  vote_count?: number;
  order: number;
}

export interface PollChoiceWithResults extends PollChoice {
  vote_count: number;
  vote_percentage: number;
}

export interface VoteRequest {
  poll_id?: string;
  choice_id: string;
}

export interface VoteResponse {
  success: boolean;
  message: string;
  points_earned: number;
}

export interface UserProfile {
  id: string;
  username: string;
  email: string;
  display_name: string;
  created_at: string;
  total_votes: number;
  accuracy_score: number;
  current_streak: number;
  longest_streak: number;
  points: number;
  level: number;
  achievements_count: number;
  achievements: Achievement[];
  recent_votes: RecentVote[];
  badges: Badge[];
  // Verification fields
  is_verified: boolean;
  email_verified: boolean;
}

export interface AchievementEarnedDate {
  earned_at: string;
  period_key?: string;
}

export interface Achievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  points_reward: number;
  is_unlocked: boolean;
  unlocked_at?: string;
  progress: number;
  target: number;
  tier?: 'bronze' | 'silver' | 'gold' | 'platinum';
  category?: 'voting' | 'streak' | 'profile' | 'leaderboard';
  is_repeatable?: boolean;
  times_earned?: number;
  earned_history?: AchievementEarnedDate[];
  // Legacy fields for backwards compatibility
  type?: string;
  unlocked?: boolean;
}

export interface Badge {
  id: string;
  name: string;
  icon: string;
  tier: 'bronze' | 'silver' | 'gold' | 'platinum';
}

export interface RecentVote {
  poll_id: string;
  poll_question: string;
  choice_text: string;
  voted_at: string;
  was_majority: boolean;
}

export interface LeaderboardEntry {
  rank: number;
  username: string;
  avatar_url?: string;
  points: number;
  level: number;
  level_name: string;
}

export interface LeaderboardResponse {
  entries: LeaderboardEntry[];
  period: string;
  total_participants: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export interface VoteStatusResponse {
  poll_id: string;
  has_voted: boolean;
}

export interface DemographicChoiceBreakdown {
  choice_text: string;
  count: number;
  percentage: number;
}

export interface DemographicSegment {
  name: string;
  votes: number;
  choices: DemographicChoiceBreakdown[];
}

export interface DemographicBreakdown {
  category: string;
  label: string;
  segments: DemographicSegment[];
}

export interface PollDemographicsResponse {
  poll_id: string;
  total_votes: number;
  breakdowns: DemographicBreakdown[];
}

export interface UserDemographics {
  age_range?: string;
  gender?: string;
  country?: string;
  region?: string;
  state_province?: string;
  city?: string;
  education_level?: string;
  employment_status?: string;
  industry?: string;
  political_leaning?: string;
  // New fields
  marital_status?: string;
  religious_affiliation?: string;
  ethnicity?: string;
  household_income?: string;
  parental_status?: string;
  housing_status?: string;
}

export interface DemographicsUpdate {
  age_range?: string;
  gender?: string;
  country?: string;
  region?: string;
  state_province?: string;
  city?: string;
  education_level?: string;
  employment_status?: string;
  industry?: string;
  political_leaning?: string;
  // New fields
  marital_status?: string;
  religious_affiliation?: string;
  ethnicity?: string;
  household_income?: string;
  parental_status?: string;
  housing_status?: string;
}

export interface DemographicsUpdateResponse {
  demographics: UserDemographics;
  points_earned: number;
  points_breakdown: Record<string, number>;
  new_total_points: number;
  message: string;
}

// Location types
export interface LocationCountry {
  code: string;
  name: string;
}

export interface LocationState {
  id: number;
  code: string | null;
  name: string;
  country_code: string;
}

export interface LocationCity {
  id: number;
  name: string;
  state_id: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: UserProfile;
}

export interface LoginRequest {
  email: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  display_name?: string;
}

export type ThemePreference = 'light' | 'dark' | 'system';

export interface UserSettings {
  email_notifications: boolean;
  push_notifications: boolean;
  daily_poll_reminder: boolean;
  show_on_leaderboard: boolean;
  share_anonymous_demographics: boolean;
  theme_preference: ThemePreference;
  // Pulse and Flash poll notifications
  pulse_poll_notifications: boolean;
  flash_poll_notifications: boolean;
  flash_polls_per_day: number;
}

// Platform statistics types
export interface FormattedStats {
  polls_created: string;
  polls_created_raw: number;
  completed_polls: string;
  completed_polls_raw: number;
  votes_cast: string;
  votes_cast_raw: number;
  active_users: string;
  active_users_raw: number;
  total_users: string;
  total_users_raw: number;
  countries_represented: string;
  countries_represented_raw: number;
}

export interface PlatformStatsResponse {
  stats: FormattedStats;
  computed_at: string;
  cache_ttl_hours: number;
  next_refresh_at: string;
}

// Community Achievement types
export interface CommunityAchievement {
  id: string;
  name: string;
  description: string;
  icon: string;
  badge_icon: string;
  goal_type: string;
  target_count: number;
  time_window_hours?: number;
  points_reward: number;
  bonus_multiplier: number;
  is_recurring: boolean;
  cooldown_hours?: number;
  tier: string;
  category: string;
  is_active: boolean;
}

export interface CommunityAchievementProgress {
  achievement: CommunityAchievement;
  current_count: number;
  progress_percentage: number;
  participant_count: number;
  time_remaining_hours?: number;
  started_at?: string;
  user_participated: boolean;
  user_contribution: number;
}

export interface CommunityAchievementEvent {
  id: string;
  achievement_id: string;
  achievement_name: string;
  achievement_icon: string;
  badge_icon: string;
  triggered_at: string;
  completed_at?: string;
  final_count: number;
  participant_count: number;
  points_reward: number;
  user_earned_badge: boolean;
  user_earned_points: number;
}

export interface CommunityLeaderboardEntry {
  user_id: string;
  display_name: string;
  avatar_url?: string;
  total_contributions: number;
  achievements_participated: number;
  badges_earned: number;
}

// Ad engagement types
export interface AdEngagementRequest {
  event_type: 'view' | 'click';
  ad_type: string;
  placement: string;
}

export interface AdEngagementResponse {
  success: boolean;
  achievement_unlocked?: {
    id: string;
    name: string;
    description: string;
    points_reward: number;
  };
}

export interface AdEngagementStats {
  total_views: number;
  total_clicks: number;
  achievements_from_ads: number;
}

// API Client
class ApiClient {
  private baseUrl: string;
  private token: string | null = null;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
    if (typeof window !== 'undefined') {
      this.token = localStorage.getItem('access_token');
    }
  }

  setToken(token: string | null) {
    this.token = token;
    if (typeof window !== 'undefined') {
      if (token) {
        localStorage.setItem('access_token', token);
      } else {
        localStorage.removeItem('access_token');
      }
    }
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
      'X-Frontend-Secret': FRONTEND_API_SECRET,
      ...options.headers,
    };

    if (this.token) {
      (headers as Record<string, string>)['Authorization'] = `Bearer ${this.token}`;
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `API Error: ${response.status}`);
    }

    return response.json();
  }

  // Auth endpoints - Registration only (login is via passkeys)
  async register(data: RegisterRequest): Promise<AuthResponse> {
    const result = await this.request<AuthResponse>('/auth/register', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    this.setToken(result.access_token);
    return result;
  }

  async sendVerificationEmail(email: string): Promise<{ message: string }> {
    return this.request<{ message: string }>('/auth/send-verification-email', {
      method: 'POST',
      body: JSON.stringify({ email }),
    });
  }

  async logout(): Promise<void> {
    this.setToken(null);
  }

  async getProfile(): Promise<UserProfile> {
    return this.request<UserProfile>('/users/me');
  }

  // Poll endpoints
  
  /**
   * Get the currently active poll.
   * This is the main poll displayed on the homepage that users can vote on.
   * Polls rotate at the top of each hour.
   */
  async getCurrentPoll(): Promise<Poll | null> {
    try {
      return await this.request<Poll>('/polls/current');
    } catch {
      return null;
    }
  }

  /**
   * Get the most recently closed poll with results.
   * This is displayed on the main page to show what users voted on previously.
   */
  async getPreviousPoll(): Promise<PollWithResults | null> {
    try {
      return await this.request<PollWithResults>('/polls/previous');
    } catch {
      return null;
    }
  }

  /**
   * Get upcoming scheduled polls.
   */
  async getUpcomingPolls(limit: number = 5): Promise<Poll[]> {
    return this.request<Poll[]>(`/polls/upcoming?limit=${limit}`);
  }

  // ========================================================================
  // Pulse Poll Endpoints (Daily 12-hour polls, 8am-8pm ET)
  // ========================================================================

  /**
   * Get the current daily Pulse Poll if active.
   * Pulse Polls run daily from 8am-8pm ET (12 hours).
   */
  async getCurrentPulsePoll(): Promise<Poll | null> {
    try {
      return await this.request<Poll>('/polls/pulse/current');
    } catch {
      return null;
    }
  }

  /**
   * Get the previous Pulse Poll with results.
   */
  async getPreviousPulsePoll(): Promise<PollWithResults | null> {
    try {
      return await this.request<PollWithResults>('/polls/pulse/previous');
    } catch {
      return null;
    }
  }

  /**
   * Get historical Pulse Polls.
   */
  async getPulsePollHistory(page: number = 1, perPage: number = 10): Promise<{ polls: Poll[]; total: number }> {
    return this.request<{ polls: Poll[]; total: number }>(
      `/polls/pulse/history?page=${page}&per_page=${perPage}`
    );
  }

  // ========================================================================
  // Flash Poll Endpoints (Quick 1-hour polls every 2-3 hours)
  // ========================================================================

  /**
   * Get the current Flash Poll if active.
   * Flash Polls run every 2-3 hours, 24/7, with 1-hour duration.
   */
  async getCurrentFlashPoll(): Promise<Poll | null> {
    try {
      return await this.request<Poll>('/polls/flash/current');
    } catch {
      return null;
    }
  }

  /**
   * Get the previous Flash Poll with results.
   */
  async getPreviousFlashPoll(): Promise<PollWithResults | null> {
    try {
      return await this.request<PollWithResults>('/polls/flash/previous');
    } catch {
      return null;
    }
  }

  /**
   * Get upcoming Flash Polls.
   */
  async getUpcomingFlashPolls(limit: number = 5): Promise<Poll[]> {
    return this.request<Poll[]>(`/polls/flash/upcoming?limit=${limit}`);
  }

  /**
   * Get historical Flash Polls.
   */
  async getFlashPollHistory(page: number = 1, perPage: number = 20): Promise<{ polls: Poll[]; total: number }> {
    return this.request<{ polls: Poll[]; total: number }>(
      `/polls/flash/history?page=${page}&per_page=${perPage}`
    );
  }

  async getPolls(params?: { category?: string; active?: boolean }): Promise<Poll[]> {
    const queryParams = new URLSearchParams();
    if (params?.category) queryParams.append('category', params.category);
    if (params?.active !== undefined) queryParams.append('active', String(params.active));
    
    const query = queryParams.toString();
    return this.request<Poll[]>(`/polls${query ? `?${query}` : ''}`);
  }

  async getPoll(id: string): Promise<Poll> {
    return this.request<Poll>(`/polls/${id}`);
  }

  async vote(pollId: string, data: VoteRequest): Promise<VoteResponse> {
    return this.request<VoteResponse>('/votes', {
      method: 'POST',
      body: JSON.stringify({ poll_id: pollId, choice_id: data.choice_id }),
    });
  }

  async getPollResults(pollId: string): Promise<PollWithResults> {
    return this.request<PollWithResults>(`/polls/${pollId}/results`);
  }

  async getPollDemographics(pollId: string): Promise<PollDemographicsResponse> {
    return this.request<PollDemographicsResponse>(`/polls/${pollId}/demographics`);
  }

  // Leaderboard endpoints
  async getLeaderboard(params?: {
    timeframe?: 'daily' | 'weekly' | 'monthly' | 'all_time';
    limit?: number;
  }): Promise<LeaderboardEntry[]> {
    const queryParams = new URLSearchParams();
    if (params?.timeframe) {
      // Convert all_time to alltime for backend compatibility
      const period = params.timeframe === 'all_time' ? 'alltime' : params.timeframe;
      queryParams.append('period', period);
    }
    if (params?.limit) queryParams.append('per_page', String(params.limit));
    
    const query = queryParams.toString();
    const response = await this.request<LeaderboardResponse>(`/gamification/leaderboard${query ? `?${query}` : ''}`);
    return response.entries;
  }

  // Vote status check
  async checkVoteStatus(pollId: string): Promise<VoteStatusResponse> {
    return this.request<VoteStatusResponse>(`/votes/status/${pollId}`);
  }

  // User stats
  async getUserStats(): Promise<{
    total_votes: number;
    accuracy_score: number;
    current_streak: number;
    points: number;
  }> {
    return this.request('/users/me/stats');
  }

  // Achievements
  async getAchievements(): Promise<Achievement[]> {
    return this.request<Achievement[]>('/gamification/achievements');
  }

  // All achievements (public - no auth required)
  async getAllAchievements(params?: {
    category?: string;
    tier?: string;
    search?: string;
  }): Promise<Achievement[]> {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set('category', params.category);
    if (params?.tier) searchParams.set('tier', params.tier);
    if (params?.search) searchParams.set('search', params.search);
    const queryString = searchParams.toString();
    return this.request<Achievement[]>(`/gamification/achievements/all${queryString ? `?${queryString}` : ''}`);
  }

  // User achievements with progress (auth required)
  async getUserAchievements(params?: {
    category?: string;
    tier?: string;
    search?: string;
    unlocked_only?: boolean;
  }): Promise<Achievement[]> {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set('category', params.category);
    if (params?.tier) searchParams.set('tier', params.tier);
    if (params?.search) searchParams.set('search', params.search);
    if (params?.unlocked_only) searchParams.set('unlocked_only', 'true');
    const queryString = searchParams.toString();
    return this.request<Achievement[]>(`/gamification/achievements/user${queryString ? `?${queryString}` : ''}`);
  }

  // Update profile
  async updateProfile(data: { display_name: string }): Promise<UserProfile> {
    return this.request<UserProfile>('/users/me', {
      method: 'PATCH',
      body: JSON.stringify(data),
    });
  }

  // User settings (includes theme preference)
  async getSettings(): Promise<UserSettings> {
    return this.request<UserSettings>('/users/me/settings');
  }

  async updateSettings(data: Partial<UserSettings>): Promise<UserSettings> {
    return this.request<UserSettings>('/users/me/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async updateThemePreference(theme: ThemePreference): Promise<UserSettings> {
    return this.updateSettings({ theme_preference: theme });
  }

  // Demographics
  async updateDemographics(data: DemographicsUpdate): Promise<DemographicsUpdateResponse> {
    return this.request<DemographicsUpdateResponse>('/users/me/demographics', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async getDemographics(): Promise<UserDemographics> {
    return this.request<UserDemographics>('/users/me/demographics');
  }

  // Location endpoints
  async getCountries(search?: string): Promise<LocationCountry[]> {
    const params = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.request<LocationCountry[]>(`/locations/countries${params}`);
  }

  async getStatesByCountry(countryCode: string, search?: string): Promise<LocationState[]> {
    const params = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.request<LocationState[]>(`/locations/countries/${countryCode}/states${params}`);
  }

  async getCitiesByState(stateId: number, search?: string): Promise<LocationCity[]> {
    const params = search ? `?search=${encodeURIComponent(search)}` : '';
    return this.request<LocationCity[]>(`/locations/states/${stateId}/cities${params}`);
  }

  // Platform Statistics
  /**
   * Get platform-wide statistics (polls created, votes cast, active users).
   * Data is cached server-side and refreshed periodically (default: 24 hours).
   * This is a public endpoint - no authentication required.
   */
  async getPlatformStats(): Promise<PlatformStatsResponse> {
    return this.request<PlatformStatsResponse>('/stats/');
  }

  // Ad engagement tracking
  /**
   * Track ad engagement for achievements and analytics.
   * Requires authentication to award achievements.
   */
  async trackAdEngagement(data: AdEngagementRequest): Promise<AdEngagementResponse> {
    return this.request<AdEngagementResponse>('/ads/engagement', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  /**
   * Get user's ad engagement stats.
   */
  async getAdEngagementStats(): Promise<AdEngagementStats> {
    return this.request<AdEngagementStats>('/ads/stats');
  }

  // ========================================================================
  // Community Achievement Endpoints
  // ========================================================================

  /**
   * Get all active community achievements with current progress.
   * Shows collective goals the community is working towards.
   */
  async getActiveCommunityAchievements(): Promise<CommunityAchievementProgress[]> {
    return this.request<CommunityAchievementProgress[]>('/community-achievements/active');
  }

  /**
   * Get recently completed community achievements.
   */
  async getCompletedCommunityAchievements(
    page: number = 1,
    perPage: number = 10
  ): Promise<CommunityAchievementEvent[]> {
    return this.request<CommunityAchievementEvent[]>(
      `/community-achievements/completed?page=${page}&per_page=${perPage}`
    );
  }

  /**
   * Get user's earned community badges.
   */
  async getUserCommunityBadges(): Promise<CommunityAchievementEvent[]> {
    return this.request<CommunityAchievementEvent[]>('/community-achievements/user/badges');
  }

  /**
   * Get community achievement leaderboard.
   */
  async getCommunityLeaderboard(limit: number = 20): Promise<CommunityLeaderboardEntry[]> {
    return this.request<CommunityLeaderboardEntry[]>(
      `/community-achievements/leaderboard?limit=${limit}`
    );
  }

  /**
   * Get details of a specific community achievement.
   */
  async getCommunityAchievement(achievementId: string): Promise<CommunityAchievementProgress> {
    return this.request<CommunityAchievementProgress>(
      `/community-achievements/${achievementId}`
    );
  }
}

export const api = new ApiClient(API_BASE_URL);
