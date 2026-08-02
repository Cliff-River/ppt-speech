import { notFound } from "next/navigation";

import { isLocale } from "@/i18n/config";
import { HomeClient } from "@/features/home/HomeClient";

export default async function Page({
  params,
}: {
  params: Promise<{ locale: string }>;
}) {
  const resolved = await params;
  if (!isLocale(resolved.locale)) {
    notFound();
  }

  return <HomeClient locale={resolved.locale} />;
}
