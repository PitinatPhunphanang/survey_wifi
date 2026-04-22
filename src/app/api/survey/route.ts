import { NextResponse } from "next/server";
import { createAdminClient } from "@/lib/supabase/admin";

export async function GET() {
  const supabase = createAdminClient();

  const { data, error } = await supabase
    .from("surveys")
    .select("*")
    .order("survey_timestamp", { ascending: false });

  if (error) {
    return NextResponse.json({ error: error.message }, { status: 500 });
  }

  return NextResponse.json(data ?? []);
}

export async function DELETE(req: Request) {
  try {
    const { scope, building, floor } = await req.json();

    if (!building) {
      return NextResponse.json({ error: "building is required" }, { status: 400 });
    }

    const supabase = createAdminClient();

    let query = supabase
      .from("surveys")
      .delete()
      .eq("building", building);

    if (scope === "floor") {
      if (!floor) {
        return NextResponse.json({ error: "floor is required" }, { status: 400 });
      }
      query = query.eq("floor", floor);
    }

    const { data, error } = await query.select("id");

    if (error) {
      return NextResponse.json({ error: error.message }, { status: 500 });
    }

    return NextResponse.json({
      success: true,
      deletedCount: data?.length ?? 0,
    });
  } catch (error) {
    return NextResponse.json(
      { error: "Invalid request body" },
      { status: 400 }
    );
  }
}