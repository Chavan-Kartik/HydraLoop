import { Scoreboard } from "@/components/Scoreboard";
import { PageHeader } from "@/components/ui";

export default function ScoreboardPage() {
  return (
    <div>
      <PageHeader
        eyebrow="Defend"
        title="Metrics"
        subtitle="Did the loop actually work? Escape rate should fall generation over generation while archive recall holds, and every promotion or rollback the gauntlet decided is logged underneath."
      />
      <Scoreboard />
    </div>
  );
}
