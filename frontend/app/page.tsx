import HeroSection from '@/components/landing/HeroSection';
import FeaturesSection from '@/components/landing/FeaturesSection';
import HowItWorksSection from '@/components/landing/HowItWorksSection';

export default function LandingPage() {
  return (
    <main className="relative overflow-x-hidden pb-20">
      <HeroSection />
      <FeaturesSection />
      <HowItWorksSection />
    </main>
  );
}
