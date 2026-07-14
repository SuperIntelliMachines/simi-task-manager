import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ChannelsPage } from "./channels";
import { renderWithApp } from "../test/render-app";

describe("ChannelsPage", () => {
  it("validates required channel fields", async () => {
    const user = userEvent.setup();
    renderWithApp(<ChannelsPage />);

    const whatsappCard = await screen.findByTestId("whatsapp-channel-card");
    const providerField = within(whatsappCard).getByLabelText(/Provider Reference/i);
    const settingField = within(whatsappCard).getByLabelText(/Phone Number ID/i);

    await user.clear(providerField);
    await user.clear(settingField);
    await user.click(within(whatsappCard).getByRole("button", { name: /Save Connection/i }));

    expect(await within(whatsappCard).findByText(/Provider reference is required/i)).toBeInTheDocument();
    expect(within(whatsappCard).getByText(/A channel setting is required/i)).toBeInTheDocument();
  });
});
