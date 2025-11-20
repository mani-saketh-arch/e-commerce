"""
Email Service
Send transactional emails using SMTP (Gmail/SendGrid)
Located at: app/services/email_service.py
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime

from app.config import settings


class EmailService:
    """Service for sending emails via SMTP"""
    
    @staticmethod
    def send_email(
        to_email: str,
        subject: str,
        html_content: str,
        plain_content: Optional[str] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML email body
            plain_content: Plain text email body (optional)
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = f"{settings.SMTP_FROM_NAME} <{settings.SMTP_FROM_EMAIL}>"
            msg['To'] = to_email
            msg['Subject'] = subject
            
            # Add plain text version if provided
            if plain_content:
                part1 = MIMEText(plain_content, 'plain')
                msg.attach(part1)
            
            # Add HTML version
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            print(f"✅ Email sent to {to_email}: {subject}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email to {to_email}: {str(e)}")
            return False
    
    
    @staticmethod
    def send_order_confirmation(
        to_email: str,
        order_number: str,
        customer_name: str,
        order_items: list,
        total_amount: float,
        shipping_address: dict
    ) -> bool:
        """
        Send order confirmation email
        
        Args:
            to_email: Customer email
            order_number: Order number
            customer_name: Customer name
            order_items: List of order items
            total_amount: Total order amount
            shipping_address: Shipping address dict
            
        Returns:
            True if sent successfully
        """
        subject = f"Order Confirmed - {order_number}"
        
        # Build items list HTML
        items_html = ""
        for item in order_items:
            items_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">
                    {item.get('product_name')}
                    {f"({item.get('size')}, {item.get('color')})" if item.get('size') or item.get('color') else ''}
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">
                    {item.get('quantity')}
                </td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">
                    ₹{item.get('subtotal', 0):.2f}
                </td>
            </tr>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px;">
                <h1 style="margin: 0;">Order Confirmed! 🎉</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f9f9f9; margin-top: 20px; border-radius: 5px;">
                <p>Hi <strong>{customer_name}</strong>,</p>
                <p>Thank you for your order! We're excited to get your items to you.</p>
                
                <h2 style="color: #4CAF50;">Order Details</h2>
                <p><strong>Order Number:</strong> {order_number}</p>
                <p><strong>Order Date:</strong> {datetime.now().strftime('%B %d, %Y')}</p>
                
                <h3>Items Ordered</h3>
                <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                    <thead>
                        <tr style="background-color: #f0f0f0;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Product</th>
                            <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Qty</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Price</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                    <tfoot>
                        <tr style="background-color: #f0f0f0; font-weight: bold;">
                            <td colspan="2" style="padding: 10px; text-align: right;">Total:</td>
                            <td style="padding: 10px; text-align: right;">₹{total_amount:.2f}</td>
                        </tr>
                    </tfoot>
                </table>
                
                <h3 style="margin-top: 20px;">Shipping Address</h3>
                <p style="margin: 5px 0;">
                    {shipping_address.get('line1')}<br>
                    {shipping_address.get('line2', '')}<br>
                    {shipping_address.get('city')}, {shipping_address.get('state')} {shipping_address.get('pincode')}<br>
                    {shipping_address.get('country', 'India')}
                </p>
                
                <div style="margin-top: 30px; padding: 15px; background-color: #e8f5e9; border-left: 4px solid #4CAF50; border-radius: 3px;">
                    <p style="margin: 0;"><strong>What's Next?</strong></p>
                    <p style="margin: 5px 0 0 0;">We'll send you another email once your order ships with tracking information.</p>
                </div>
                
                <p style="margin-top: 30px; text-align: center;">
                    <a href="http://localhost:5173/track-order" style="display: inline-block; padding: 12px 30px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Track Your Order</a>
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
                <p>Thank you for shopping with us!</p>
                <p>{settings.SMTP_FROM_NAME} | support@store.com</p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
        Order Confirmed - {order_number}
        
        Hi {customer_name},
        
        Thank you for your order! Order Number: {order_number}
        
        Total Amount: ₹{total_amount:.2f}
        
        Shipping to:
        {shipping_address.get('line1')}
        {shipping_address.get('city')}, {shipping_address.get('state')} {shipping_address.get('pincode')}
        
        Track your order: http://localhost:5173/track-order
        
        Thank you for shopping with us!
        {settings.SMTP_FROM_NAME}
        """
        
        return EmailService.send_email(to_email, subject, html_content, plain_content)
    
    
    @staticmethod
    def send_order_shipped(
        to_email: str,
        order_number: str,
        customer_name: str,
        tracking_number: str,
        courier_name: str
    ) -> bool:
        """
        Send order shipped notification
        
        Args:
            to_email: Customer email
            order_number: Order number
            customer_name: Customer name
            tracking_number: Tracking number
            courier_name: Courier service name
            
        Returns:
            True if sent successfully
        """
        subject = f"Your Order Has Been Shipped - {order_number}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #2196F3; color: white; padding: 20px; text-align: center; border-radius: 5px;">
                <h1 style="margin: 0;">Your Order is On Its Way! 📦</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f9f9f9; margin-top: 20px; border-radius: 5px;">
                <p>Hi <strong>{customer_name}</strong>,</p>
                <p>Great news! Your order has been shipped and is on its way to you.</p>
                
                <div style="background-color: white; padding: 20px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0; color: #2196F3;">Tracking Information</h3>
                    <p><strong>Order Number:</strong> {order_number}</p>
                    <p><strong>Courier:</strong> {courier_name}</p>
                </div>
                
                <div style="margin-top: 30px; padding: 15px; background-color: #e3f2fd; border-left: 4px solid #2196F3; border-radius: 3px;">
                    <p style="margin: 0;"><strong>Expected Delivery</strong></p>
                    <p style="margin: 5px 0 0 0;">Your order should arrive within 3-5 business days.</p>
                </div>
                
                <p style="margin-top: 30px; text-align: center;">
                    <a href="http://localhost:5173/track-order" style="display: inline-block; padding: 12px 30px; background-color: #2196F3; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Track Your Package</a>
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
                <p>Thank you for shopping with us!</p>
                <p>{settings.SMTP_FROM_NAME} | support@store.com</p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
        Your Order Has Been Shipped - {order_number}
        
        Hi {customer_name},
        
        Your order has been shipped!
        
        Courier: {courier_name}
       
        
        Track your package: http://localhost:5173/track-order
        
        Expected delivery: 3-5 business days
        
        Thank you!
        {settings.SMTP_FROM_NAME}
        """
        
        return EmailService.send_email(to_email, subject, html_content, plain_content)
    
    
    @staticmethod
    def send_order_delivered(
        to_email: str,
        order_number: str,
        customer_name: str
    ) -> bool:
        """
        Send order delivered notification
        
        Args:
            to_email: Customer email
            order_number: Order number
            customer_name: Customer name
            
        Returns:
            True if sent successfully
        """
        subject = f"Order Delivered - {order_number}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px;">
                <h1 style="margin: 0;">Your Order Has Been Delivered! ✅</h1>
            </div>
            
            <div style="padding: 20px; background-color: #f9f9f9; margin-top: 20px; border-radius: 5px;">
                <p>Hi <strong>{customer_name}</strong>,</p>
                <p>Your order <strong>{order_number}</strong> has been successfully delivered!</p>
                
                <p>We hope you love your new items! If you have any issues or concerns, please don't hesitate to contact us.</p>
                
                <div style="margin-top: 30px; padding: 15px; background-color: #fff3cd; border-left: 4px solid #ffc107; border-radius: 3px;">
                    <p style="margin: 0;"><strong>How did we do?</strong></p>
                    <p style="margin: 5px 0 0 0;">We'd love to hear about your experience!</p>
                </div>
                
                <p style="margin-top: 30px; text-align: center;">
                    <a href="http://localhost:5173/" style="display: inline-block; padding: 12px 30px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px; font-weight: bold;">Shop Again</a>
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; font-size: 12px;">
                <p>Thank you for shopping with us!</p>
                <p>{settings.SMTP_FROM_NAME} | support@store.com</p>
            </div>
        </body>
        </html>
        """
        
        plain_content = f"""
        Order Delivered - {order_number}
        
        Hi {customer_name},
        
        Your order {order_number} has been successfully delivered!
        
        We hope you love your new items!
        
        Shop again: http://localhost:5173/
        
        Thank you!
        {settings.SMTP_FROM_NAME}
        """
        
        return EmailService.send_email(to_email, subject, html_content, plain_content)
    
    
    @staticmethod
    def send_admin_new_order_alert(
        admin_email: str,
        order_number: str,
        customer_name: str,
        total_amount: float,
        item_count: int
    ) -> bool:
        """
        Send new order alert to admin
        
        Args:
            admin_email: Admin email address
            order_number: Order number
            customer_name: Customer name
            total_amount: Total order amount
            item_count: Number of items
            
        Returns:
            True if sent successfully
        """
        subject = f"New Order Received - {order_number}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2>🎉 New Order Received!</h2>
            <p><strong>Order Number:</strong> {order_number}</p>
            <p><strong>Customer:</strong> {customer_name}</p>
            <p><strong>Items:</strong> {item_count}</p>
            <p><strong>Total Amount:</strong> ₹{total_amount:.2f}</p>
            <p><strong>Time:</strong> {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            <p><a href="http://localhost:5174/orders" style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: white; text-decoration: none; border-radius: 5px;">View Order</a></p>
        </body>
        </html>
        """
        
        return EmailService.send_email(admin_email, subject, html_content)


# Export singleton instance
email_service = EmailService()