import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

export async function GET() {
    const supabase = createAdminClient();

    const { data, error } = await supabase
        .from("surveys")
        .select("*")
        .order("survey_timestamp", { ascending: false })
        .limit(1);

    if (error) {
        return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json(data?.[0] ?? null);
}