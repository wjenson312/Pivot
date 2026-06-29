import { redirect } from "next/navigation";

// The Database tab is the dashboard's primary entry point — pick a run there
// before any Data Analysis tab has something to show.
export default function HomePage() {
  redirect("/database");
}
