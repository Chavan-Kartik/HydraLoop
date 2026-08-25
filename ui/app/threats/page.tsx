import { ThreatBoard } from "@/components/ThreatBoard";
import { PageHeader } from "@/components/ui";

export default function ThreatsPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Identify"
        title="Threat Board"
        subtitle="Catalog of bounded scenarios. Each card can be sent into the Lab, where you watch the full Identify-to-Detect pipeline run on that pattern rather than reading a static description."
      />
      <ThreatBoard />
    </div>
  );
}
