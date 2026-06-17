<%@ Page Title="Company Registration" Language="C#" MasterPageFile="~/Site.Master" AutoEventWireup="true" CodeBehind="NewCompany.aspx.cs" Inherits="NewHireCompanyManager.NewCompany" %>

<asp:Content ID="Content1" ContentPlaceHolderID="MainContent" runat="server">
    <div class="page-header">
        <h1><asp:Literal ID="PageTitleLiteral" runat="server" Text="Create Company" /></h1>
    </div>

    <asp:ValidationSummary ID="ValidationSummary1" runat="server" CssClass="alert alert-danger" HeaderText="Please fix the following:" />
    <asp:Label ID="MessageLabel" runat="server" CssClass="alert alert-success" Visible="false" />

    <div class="form-panel">
        <div class="row">
            <div class="col-sm-6 form-group">
                <label>Company Name <span class="required">(R)</span></label>
                <asp:TextBox ID="CompanyNameTextBox" runat="server" CssClass="form-control" MaxLength="150" />
                <asp:RequiredFieldValidator ID="CompanyNameValidator" runat="server" ControlToValidate="CompanyNameTextBox" ErrorMessage="Company Name is required." Display="Dynamic" CssClass="field-validation-error" />
            </div>
            <div class="col-sm-6 form-group">
                <label>Company Identifier <span class="required">(R)</span></label>
                <asp:TextBox ID="CompanyIdentifierTextBox" runat="server" CssClass="form-control" MaxLength="50" />
                <asp:RequiredFieldValidator ID="CompanyIdentifierValidator" runat="server" ControlToValidate="CompanyIdentifierTextBox" ErrorMessage="Company Identifier is required." Display="Dynamic" CssClass="field-validation-error" />
            </div>
        </div>

        <div class="row">
            <div class="col-sm-6 form-group">
                <label>Company Logo</label>
                <asp:FileUpload ID="LogoUpload" runat="server" CssClass="form-control" />
                <asp:Literal ID="ExistingLogoLiteral" runat="server" />
            </div>
            <div class="col-sm-6 form-group">
                <label>Phone Number</label>
                <asp:TextBox ID="PhoneNumberTextBox" runat="server" CssClass="form-control" MaxLength="25" />
            </div>
        </div>

        <div class="row">
            <div class="col-sm-6 form-group">
                <label>Address 1</label>
                <asp:TextBox ID="Address1TextBox" runat="server" CssClass="form-control" MaxLength="150" />
            </div>
            <div class="col-sm-6 form-group">
                <label>Address 2</label>
                <asp:TextBox ID="Address2TextBox" runat="server" CssClass="form-control" MaxLength="150" />
            </div>
        </div>

        <div class="row">
            <div class="col-sm-4 form-group">
                <label>City</label>
                <asp:TextBox ID="CityTextBox" runat="server" CssClass="form-control" MaxLength="80" />
            </div>
            <div class="col-sm-4 form-group">
                <label>State</label>
                <asp:DropDownList ID="StateDropDown" runat="server" CssClass="form-control" />
            </div>
            <div class="col-sm-4 form-group">
                <label>Zip</label>
                <asp:TextBox ID="ZipTextBox" runat="server" CssClass="form-control" MaxLength="15" />
            </div>
        </div>

        <div class="row">
            <div class="col-sm-6 form-group">
                <label>Primary Contact <span class="required">(R)</span></label>
                <asp:TextBox ID="PrimaryContactTextBox" runat="server" CssClass="form-control" MaxLength="150" />
                <asp:RequiredFieldValidator ID="PrimaryContactValidator" runat="server" ControlToValidate="PrimaryContactTextBox" ErrorMessage="Primary Contact is required." Display="Dynamic" CssClass="field-validation-error" />
            </div>
            <div class="col-sm-6 form-group">
                <label>Point Of Contact Email <span class="required">(R)</span></label>
                <asp:TextBox ID="EmailTextBox" runat="server" CssClass="form-control" MaxLength="150" TextMode="Email" />
                <asp:RequiredFieldValidator ID="EmailRequiredValidator" runat="server" ControlToValidate="EmailTextBox" ErrorMessage="Point Of Contact Email is required." Display="Dynamic" CssClass="field-validation-error" />
                <asp:RegularExpressionValidator ID="EmailFormatValidator" runat="server" ControlToValidate="EmailTextBox" ErrorMessage="Point Of Contact Email must be a valid email address." Display="Dynamic" CssClass="field-validation-error" ValidationExpression="^[^@\s]+@[^@\s]+\.[^@\s]+$" />
            </div>
        </div>

        <div class="row">
            <div class="col-sm-6 form-group">
                <label>Tax-ID <span class="required">(R)</span></label>
                <asp:TextBox ID="TaxIdTextBox" runat="server" CssClass="form-control" MaxLength="25" />
                <asp:RequiredFieldValidator ID="TaxIdValidator" runat="server" ControlToValidate="TaxIdTextBox" ErrorMessage="Tax-ID is required." Display="Dynamic" CssClass="field-validation-error" />
            </div>
            <div class="col-sm-6 form-group">
                <label>Bank Name <span class="required">(R)</span></label>
                <asp:TextBox ID="BankNameTextBox" runat="server" CssClass="form-control" MaxLength="150" />
                <asp:RequiredFieldValidator ID="BankNameValidator" runat="server" ControlToValidate="BankNameTextBox" ErrorMessage="Bank Name is required." Display="Dynamic" CssClass="field-validation-error" />
            </div>
        </div>

        <div class="row">
            <div class="col-sm-4 form-group">
                <label>1099 Line Break Field</label>
                <div class="checkbox">
                    <label><asp:CheckBox ID="Form1099CheckBox" runat="server" /> Enabled</label>
                </div>
            </div>
            <div class="col-sm-4 form-group">
                <label>Withholding Number</label>
                <asp:TextBox ID="WithholdingNumberTextBox" runat="server" CssClass="form-control" MaxLength="50" />
            </div>
            <div class="col-sm-4 form-group">
                <label>County</label>
                <asp:TextBox ID="CountyTextBox" runat="server" CssClass="form-control" MaxLength="80" />
            </div>
        </div>

        <h3>Company Modules</h3>
        <asp:CheckBoxList ID="ModulesCheckBoxList" runat="server" CssClass="module-list" RepeatColumns="2" RepeatDirection="Vertical" />

        <hr />
        <asp:Button ID="SaveButton" runat="server" Text="Save Company" CssClass="btn btn-primary" OnClick="SaveButton_Click" />
        <asp:Button ID="CancelButton" runat="server" Text="Cancel" CssClass="btn btn-default" CausesValidation="false" OnClick="CancelButton_Click" />
    </div>
</asp:Content>
