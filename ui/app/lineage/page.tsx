import { Lineage } from "@/components/Lineage";
import { PageHeader } from "@/components/ui";

export default function LineagePage() {
  return (
    <div>
      <PageHeader
        eyebrow="Generate"
        title="Attack Genome Lineage"
        subtitle="How escape modes mutate across generations, and how the blue team shrinks each one. Click any node for a plain-English attack brief."
      />
      <Lineage />
    </div>
  );
}
