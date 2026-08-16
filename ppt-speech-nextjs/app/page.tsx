import { useTranslations } from "next-intl";


export default function Home() {
  const t = useTranslations("app");

  return (
    <div>
      {t("title")}
    </div>
  );
}
