"use client";

import ReviewView from "@/components/stages/ReviewView";
import { sampleReviewFindings } from "@/data/stage-details";

export default function ReviewPage() {
  return <ReviewView findings={sampleReviewFindings} />;
}
