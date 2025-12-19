import { PollCard } from '@/components/polls/poll-card';
import { HeroSection } from '@/components/home/hero-section';
import { StatsSection } from '@/components/home/stats-section';
import { HowItWorks } from '@/components/home/how-it-works';
import { FeaturedPolls } from '@/components/home/featured-polls';
import { TrustBanner } from '@/components/ui/trust-badge';
import { CommunityAchievementsWidget } from '@/components/home/community-achievements';

export default function HomePage() {
  return (
    <div className="pb-16">
      <HeroSection />
      <TrustBanner className="border-y border-gray-200 dark:border-gray-700" />
      <div className="space-y-16 mt-16">
        <FeaturedPolls />
        
        {/* Community Achievements Widget */}
        <section className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="max-w-md mx-auto lg:max-w-none lg:mx-0">
            <CommunityAchievementsWidget />
          </div>
        </section>
        
        <StatsSection />
        <HowItWorks />
      </div>
    </div>
  );
}
