import PollDetailClient from './poll-detail-client';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function PollDetailPage({ params }: PageProps) {
  const resolvedParams = await params;
  return <PollDetailClient pollId={resolvedParams.id} />;
}
