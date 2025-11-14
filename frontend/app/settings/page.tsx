"use client";

import { useState, useEffect } from "react";
import { useSettings, useUpdateSetting } from "@/hooks";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Loader2, Save, CheckCircle2 } from "lucide-react";

export default function SettingsPage() {
  const { data: settings, isLoading, error } = useSettings();
  const updateSetting = useUpdateSetting();
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);

  // State pour chaque setting
  const [bankroll, setBankroll] = useState({ amount: 10000, currency: "EUR" });
  const [apiKey, setApiKey] = useState({ key: "", enabled: true });
  const [frequency, setFrequency] = useState({ hours: 4, cache_minutes: 230 });
  const [email, setEmail] = useState({
    enabled: true,
    smtp_host: "smtp.gmail.com",
    smtp_port: 587,
    from: "",
    to: "",
  });
  const [thresholds, setThresholds] = useState({
    min_edge_pct: 5.0,
    min_odds: 1.5,
    max_odds: 10.0,
  });

  // Charger les settings depuis l'API
  useEffect(() => {
    if (settings) {
      settings.forEach((setting) => {
        switch (setting.key) {
          case "bankroll_initial":
            setBankroll(setting.value as any);
            break;
          case "api_key_odds":
            setApiKey(setting.value as any);
            break;
          case "collect_frequency":
            setFrequency(setting.value as any);
            break;
          case "email_alerts":
            setEmail(setting.value as any);
            break;
          case "notification_thresholds":
            setThresholds(setting.value as any);
            break;
        }
      });
    }
  }, [settings]);

  const handleSave = async (key: string, value: any) => {
    try {
      await updateSetting.mutateAsync({ key, value });
      setSaveSuccess(key);
      setTimeout(() => setSaveSuccess(null), 3000);
    } catch (err) {
      console.error("Error saving setting:", err);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <Loader2 className="w-8 h-8 animate-spin text-violet-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8">
        <Card className="p-6 bg-red-500/10 border-red-500/20">
          <p className="text-red-500">Erreur de chargement des paramètres</p>
        </Card>
      </div>
    );
  }

  return (
    <div className="p-8 space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">⚙️ Paramètres</h1>
        <p className="text-gray-400">Configuration de Mon_PS</p>
      </div>

      {/* Bankroll Initial */}
      <Card className="p-6 bg-gray-900/50 border-gray-800">
        <h2 className="text-xl font-semibold text-white mb-4">💰 Bankroll Initial</h2>
        <div className="space-y-4">
          <div>
            <Label htmlFor="bankroll-amount">Montant (EUR)</Label>
            <Input
              id="bankroll-amount"
              type="number"
              value={bankroll.amount}
              onChange={(e) => setBankroll({ ...bankroll, amount: Number(e.target.value) })}
              className="mt-2"
            />
          </div>
          <Button
            onClick={() => handleSave("bankroll_initial", bankroll)}
            disabled={updateSetting.isPending}
          >
            {updateSetting.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : saveSuccess === "bankroll_initial" ? (
              <CheckCircle2 className="w-4 h-4 mr-2" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            {saveSuccess === "bankroll_initial" ? "Sauvegardé !" : "Sauvegarder"}
          </Button>
        </div>
      </Card>

      {/* API Key */}
      <Card className="p-6 bg-gray-900/50 border-gray-800">
        <h2 className="text-xl font-semibold text-white mb-4">🔑 API Key The Odds API</h2>
        <div className="space-y-4">
          <div>
            <Label htmlFor="api-key">Clé API</Label>
            <Input
              id="api-key"
              type="password"
              value={apiKey.key}
              onChange={(e) => setApiKey({ ...apiKey, key: e.target.value })}
              placeholder="Votre clé API"
              className="mt-2"
            />
          </div>
          <Button
            onClick={() => handleSave("api_key_odds", apiKey)}
            disabled={updateSetting.isPending}
          >
            {updateSetting.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : saveSuccess === "api_key_odds" ? (
              <CheckCircle2 className="w-4 h-4 mr-2" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            {saveSuccess === "api_key_odds" ? "Sauvegardé !" : "Sauvegarder"}
          </Button>
        </div>
      </Card>

      {/* Fréquence Collecte */}
      <Card className="p-6 bg-gray-900/50 border-gray-800">
        <h2 className="text-xl font-semibold text-white mb-4">⏱️ Fréquence Collecte Odds</h2>
        <div className="space-y-4">
          <div>
            <Label htmlFor="freq-hours">Collecte toutes les X heures</Label>
            <Input
              id="freq-hours"
              type="number"
              min="1"
              max="24"
              value={frequency.hours}
              onChange={(e) => setFrequency({ ...frequency, hours: Number(e.target.value) })}
              className="mt-2"
            />
          </div>
          <div>
            <Label htmlFor="cache-minutes">Durée cache (minutes)</Label>
            <Input
              id="cache-minutes"
              type="number"
              value={frequency.cache_minutes}
              onChange={(e) => setFrequency({ ...frequency, cache_minutes: Number(e.target.value) })}
              className="mt-2"
            />
          </div>
          <Button
            onClick={() => handleSave("collect_frequency", frequency)}
            disabled={updateSetting.isPending}
          >
            {updateSetting.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : saveSuccess === "collect_frequency" ? (
              <CheckCircle2 className="w-4 h-4 mr-2" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            {saveSuccess === "collect_frequency" ? "Sauvegardé !" : "Sauvegarder"}
          </Button>
        </div>
      </Card>

      {/* Seuils Notifications */}
      <Card className="p-6 bg-gray-900/50 border-gray-800">
        <h2 className="text-xl font-semibold text-white mb-4">🔔 Seuils Notifications</h2>
        <div className="space-y-4">
          <div>
            <Label htmlFor="min-edge">Edge minimum (%)</Label>
            <Input
              id="min-edge"
              type="number"
              step="0.1"
              value={thresholds.min_edge_pct}
              onChange={(e) => setThresholds({ ...thresholds, min_edge_pct: Number(e.target.value) })}
              className="mt-2"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="min-odds">Cote minimum</Label>
              <Input
                id="min-odds"
                type="number"
                step="0.1"
                value={thresholds.min_odds}
                onChange={(e) => setThresholds({ ...thresholds, min_odds: Number(e.target.value) })}
                className="mt-2"
              />
            </div>
            <div>
              <Label htmlFor="max-odds">Cote maximum</Label>
              <Input
                id="max-odds"
                type="number"
                step="0.1"
                value={thresholds.max_odds}
                onChange={(e) => setThresholds({ ...thresholds, max_odds: Number(e.target.value) })}
                className="mt-2"
              />
            </div>
          </div>
          <Button
            onClick={() => handleSave("notification_thresholds", thresholds)}
            disabled={updateSetting.isPending}
          >
            {updateSetting.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin mr-2" />
            ) : saveSuccess === "notification_thresholds" ? (
              <CheckCircle2 className="w-4 h-4 mr-2" />
            ) : (
              <Save className="w-4 h-4 mr-2" />
            )}
            {saveSuccess === "notification_thresholds" ? "Sauvegardé !" : "Sauvegarder"}
          </Button>
        </div>
      </Card>
    </div>
  );
}
