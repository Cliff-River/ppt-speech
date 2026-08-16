import { notFound } from "next/navigation";

import { I18nProvider } from "@/i18n/I18nProvider";
import { isLocale, locales } from "@/i18n/config";
import { getMessages } from "@/i18n/messages";

export function generateStaticParams() {
  return locales.map((locale) => ({ locale }));
}

export default async function LocaleLayout({
  children,
  params,
}: {
  children: React.ReactNode;
  params: Promise<{ locale: string }>;
}) {
  const resolved = await params;
  if (!isLocale(resolved.locale)) {
    notFound();
  }

  const messages = getMessages(resolved.locale);

  return (
    <I18nProvider locale={resolved.locale} messages={messages}>
      {children}
    </I18nProvider>
  );
}
