import { Suspense } from "react";
import { Lab } from "@/components/Lab";

export default function HomePage() {
  return (
    <Suspense fallback={<div className="text-sm text-ink-ghost">Loading lab</div>}>
      <Lab />
    </Suspense>
  );
}
