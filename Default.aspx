<%@ Page Title="Companies" Language="C#" MasterPageFile="~/Site.Master" AutoEventWireup="true" CodeBehind="Default.aspx.cs" Inherits="NewHireCompanyManager.Default" %>

<asp:Content ID="Content1" ContentPlaceHolderID="MainContent" runat="server">
    <div class="page-header">
        <h1>Companies</h1>
    </div>

    <asp:Label ID="MessageLabel" runat="server" CssClass="alert alert-info" Visible="false" />

    <p>
        <asp:Button ID="CreateNewButton" runat="server" Text="Create New" CssClass="btn btn-primary" OnClick="CreateNewButton_Click" />
    </p>

    <asp:DataGrid ID="CompanyGrid"
        runat="server"
        CssClass="table table-striped table-bordered"
        AutoGenerateColumns="False"
        AllowPaging="True"
        PageSize="10"
        DataKeyField="CompanyIdentifier"
        OnPageIndexChanged="CompanyGrid_PageIndexChanged"
        OnItemCommand="CompanyGrid_ItemCommand">
        <Columns>
            <asp:BoundColumn HeaderText="Company Identifier" DataField="CompanyIdentifier" />
            <asp:BoundColumn HeaderText="Company Name" DataField="CompanyName" />
            <asp:TemplateColumn HeaderText="Actions">
                <ItemTemplate>
                    <span class="grid-actions">
                        <asp:LinkButton ID="EditButton" runat="server" Text="edit" CommandName="EditCompany" CommandArgument='<%# Eval("CompanyIdentifier") %>' CausesValidation="false" />
                        <asp:LinkButton ID="DeleteButton" runat="server" Text="delete" CommandName="DeleteCompany" CommandArgument='<%# Eval("CompanyIdentifier") %>' CausesValidation="false" OnClientClick="return confirm('Delete this company?');" />
                    </span>
                </ItemTemplate>
            </asp:TemplateColumn>
        </Columns>
        <PagerStyle Mode="NumericPages" CssClass="pagination" />
    </asp:DataGrid>
</asp:Content>
