import { Arena } from "@/components/Arena";
import { PageHeader } from "@/components/ui";

export default function ArenaPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Co-evolution"
        title="Arena replay"
        subtitle="A recorded multi-generation loop. For a live input you can type, use Lab."
      />
      <Arena />
    </div>
  );
}
